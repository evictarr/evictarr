from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.notifications import (
    NotificationConfigOut,
    NotificationConfigUpdateRequest,
    NotificationTestResponse,
)
from app.auth.dependencies import get_current_user
from app.db.base import get_db
from app.db.models import NotificationConfig, NotificationProviderName
from app.notifications.base import NotificationError
from app.notifications.dispatcher import build_provider

router = APIRouter(prefix="/api/notifications/config", tags=["notifications"], dependencies=[Depends(get_current_user)])


def _summarize(provider: NotificationProviderName, config: dict) -> dict:
    if provider == NotificationProviderName.discord:
        return {"webhook_url_set": bool(config.get("webhook_url"))}
    return {"bot_token_set": bool(config.get("bot_token")), "chat_id": config.get("chat_id")}


def _to_out(row: NotificationConfig) -> NotificationConfigOut:
    return NotificationConfigOut(
        provider=row.provider,
        enabled=row.enabled,
        config_summary=_summarize(row.provider, row.config),
        notify_on_stage=row.notify_on_stage,
        notify_on_execute=row.notify_on_execute,
        notify_daily_summary=row.notify_daily_summary,
    )


async def _get_or_404(db: AsyncSession, provider: NotificationProviderName) -> NotificationConfig:
    result = await db.execute(select(NotificationConfig).where(NotificationConfig.provider == provider))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown provider")
    return row


def _merge_config(provider: NotificationProviderName, existing: dict, incoming: dict) -> dict:
    if provider == NotificationProviderName.discord:
        return {"webhook_url": incoming.get("webhook_url") or existing.get("webhook_url")}
    return {
        "bot_token": incoming.get("bot_token") or existing.get("bot_token"),
        "chat_id": incoming.get("chat_id") or existing.get("chat_id"),
    }


@router.get("", response_model=list[NotificationConfigOut])
async def list_notification_configs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NotificationConfig))
    return [_to_out(row) for row in result.scalars().all()]


@router.put("/{provider}", response_model=NotificationConfigOut)
async def update_notification_config(
    provider: NotificationProviderName, payload: NotificationConfigUpdateRequest, db: AsyncSession = Depends(get_db)
):
    row = await _get_or_404(db, provider)
    row.config = _merge_config(provider, row.config, payload.config)
    row.enabled = payload.enabled
    row.notify_on_stage = payload.notify_on_stage
    row.notify_on_execute = payload.notify_on_execute
    row.notify_daily_summary = payload.notify_daily_summary
    await db.commit()
    await db.refresh(row)
    return _to_out(row)


@router.post("/{provider}/test", response_model=NotificationTestResponse)
async def test_notification_config(provider: NotificationProviderName, db: AsyncSession = Depends(get_db)):
    row = await _get_or_404(db, provider)
    notifier = build_provider(row)
    if notifier is None:
        return NotificationTestResponse(ok=False, detail="Not fully configured yet")
    try:
        await notifier.send("Test notification from Evictarr.")
        return NotificationTestResponse(ok=True, detail="Test message sent")
    except NotificationError as exc:
        return NotificationTestResponse(ok=False, detail=str(exc))
