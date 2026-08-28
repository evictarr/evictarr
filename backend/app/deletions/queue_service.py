from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AppSettings, PendingDeletion, PendingMediaType, PendingStatus
from app.notifications.dispatcher import notify_staged

_ACTIVE_STATUSES = (PendingStatus.pending, PendingStatus.executing)


async def find_active_by_dedupe_key(db: AsyncSession, dedupe_key: str) -> PendingDeletion | None:
    result = await db.execute(
        select(PendingDeletion).where(
            PendingDeletion.dedupe_key == dedupe_key,
            PendingDeletion.status.in_(_ACTIVE_STATUSES),
        )
    )
    return result.scalar_one_or_none()


async def _grace_period_hours(db: AsyncSession) -> int:
    result = await db.execute(select(AppSettings).where(AppSettings.id == 1))
    settings = result.scalar_one_or_none()
    return settings.default_grace_period_hours if settings else 24


async def stage(
    db: AsyncSession,
    rule_id: int | None,
    media_type: PendingMediaType,
    title: str,
    external_ids: dict,
    dedupe_key: str,
) -> PendingDeletion | None:
    """Creates a pending_deletions row unless one is already active for the
    same underlying media, so a rule that matches the same item on
    consecutive runs doesn't queue it twice."""
    existing = await find_active_by_dedupe_key(db, dedupe_key)
    if existing is not None:
        return None

    grace_hours = await _grace_period_hours(db)
    now = datetime.now(timezone.utc)
    pending = PendingDeletion(
        rule_id=rule_id,
        media_type=media_type,
        title=title,
        external_ids=external_ids,
        dedupe_key=dedupe_key,
        staged_at=now,
        grace_period_hours=grace_hours,
        execute_after=now + timedelta(hours=grace_hours),
        status=PendingStatus.pending,
    )
    db.add(pending)
    await db.commit()
    await db.refresh(pending)
    await notify_staged(db, pending)
    return pending


async def cancel(db: AsyncSession, pending_deletion_id: int, reason: str | None) -> PendingDeletion:
    pending = await db.get(PendingDeletion, pending_deletion_id)
    if pending is None:
        raise ValueError("Pending deletion not found")
    if pending.status != PendingStatus.pending:
        raise ValueError(f"Cannot cancel an item in status '{pending.status.value}'")
    pending.status = PendingStatus.cancelled
    pending.cancelled_at = datetime.now(timezone.utc)
    pending.cancelled_reason = reason
    await db.commit()
    await db.refresh(pending)
    return pending
