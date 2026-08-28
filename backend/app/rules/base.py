from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EventLevel, RunEvent


@dataclass
class RuleResult:
    scanned: int = 0
    matched: int = 0
    skipped: int = 0


async def log_event(
    db: AsyncSession,
    run_id: int,
    rule_id: int | None,
    level: EventLevel,
    media_title: str | None,
    reason: str | None,
    detail: dict | None = None,
) -> None:
    db.add(
        RunEvent(
            run_id=run_id,
            rule_id=rule_id,
            level=level,
            media_title=media_title,
            reason=reason,
            detail=detail,
        )
    )
    await db.commit()
