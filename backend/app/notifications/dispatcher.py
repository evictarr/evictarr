import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ActionLog, NotificationConfig, NotificationProviderName, OverallStatus, PendingDeletion, Run
from app.notifications.base import NotificationError, NotificationProvider
from app.notifications.discord import DiscordProvider
from app.notifications.telegram import TelegramProvider

logger = logging.getLogger(__name__)


def build_provider(config: NotificationConfig) -> NotificationProvider | None:
    if config.provider == NotificationProviderName.discord:
        webhook_url = config.config.get("webhook_url")
        return DiscordProvider(webhook_url) if webhook_url else None
    if config.provider == NotificationProviderName.telegram:
        bot_token = config.config.get("bot_token")
        chat_id = config.config.get("chat_id")
        return TelegramProvider(bot_token, chat_id) if bot_token and chat_id else None
    return None


async def _enabled_providers(db: AsyncSession, event_field: str) -> list[NotificationProvider]:
    result = await db.execute(select(NotificationConfig).where(NotificationConfig.enabled == True))  # noqa: E712
    providers = []
    for config in result.scalars().all():
        if not getattr(config, event_field):
            continue
        provider = build_provider(config)
        if provider is not None:
            providers.append(provider)
    return providers


async def _fan_out(providers: list[NotificationProvider], message: str) -> None:
    for provider in providers:
        try:
            await provider.send(message)
        except NotificationError:
            logger.exception("Notification send failed")


async def notify_staged(db: AsyncSession, pending: PendingDeletion) -> None:
    providers = await _enabled_providers(db, "notify_on_stage")
    if not providers:
        return
    message = (
        f"Queued for deletion: {pending.title}\n"
        f"Executes in {pending.grace_period_hours}h unless cancelled in Evictarr."
    )
    await _fan_out(providers, message)


async def notify_executed(db: AsyncSession, pending: PendingDeletion, action: ActionLog) -> None:
    providers = await _enabled_providers(db, "notify_on_execute")
    if not providers:
        return
    if action.overall_status == OverallStatus.success:
        message = f"Deleted: {pending.title}"
    else:
        message = f"Deletion issue for {pending.title}: {action.overall_status.value} ({action.error_detail})"
    await _fan_out(providers, message)


async def notify_run_summary(db: AsyncSession, run: Run) -> None:
    providers = await _enabled_providers(db, "notify_daily_summary")
    if not providers:
        return
    message = (
        f"Evictarr scan finished: {run.items_scanned} scanned, "
        f"{run.items_matched} matched, {run.items_skipped} skipped."
    )
    await _fan_out(providers, message)
