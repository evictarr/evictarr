from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EventLevel, Rule, RuleType, Run, RunStatus, RunType
from app.integrations.base_client import IntegrationError
from app.notifications.dispatcher import notify_run_summary
from app.rules import movie_watched, series_watched, stale_request
from app.rules.base import log_event
from app.rules.context import RuleContext

_HANDLERS = {
    RuleType.movie_watched_cleanup: movie_watched.evaluate,
    RuleType.series_watched_cleanup: series_watched.evaluate,
    RuleType.stale_request_cleanup: stale_request.evaluate,
}


async def run_scan(db: AsyncSession, run_type: RunType, triggered_by: str, rule_ids: list[int] | None = None) -> Run:
    run = Run(run_type=run_type, triggered_by=triggered_by, status=RunStatus.running)
    db.add(run)
    await db.commit()
    await db.refresh(run)

    query = select(Rule).where(Rule.enabled == True)  # noqa: E712
    if rule_ids is not None:
        query = query.where(Rule.id.in_(rule_ids))
    rules = list((await db.execute(query)).scalars().all())

    ctx = RuleContext(db)
    scanned = matched = skipped = 0

    for rule in rules:
        handler = _HANDLERS.get(rule.rule_type)
        if handler is None:
            continue  # orphaned_scan is handled by its own separate feature, not the deletion pipeline
        try:
            result = await handler(db, run.id, rule, ctx)
        except IntegrationError as exc:
            await log_event(db, run.id, rule.id, EventLevel.error, None, str(exc))
            continue
        scanned += result.scanned
        matched += result.matched
        skipped += result.skipped

    run.status = RunStatus.completed
    run.finished_at = datetime.now(timezone.utc)
    run.items_scanned = scanned
    run.items_matched = matched
    run.items_skipped = skipped
    await db.commit()
    await db.refresh(run)

    # Only the unattended scheduled run gets a summary notification - a
    # manual "Run now" click means the user is already watching the result
    # in the UI, so pinging Discord/Telegram too would just be noise.
    if run_type == RunType.scheduled:
        await notify_run_summary(db, run)

    return run


_WATCHED_RULE_TYPES = (RuleType.movie_watched_cleanup, RuleType.series_watched_cleanup)

# Looked up as modules (not `_HANDLERS`, which captures the `.evaluate`
# function object at import time) so tests can monkeypatch
# `movie_watched.evaluate` / `series_watched.evaluate` directly.
_WATCHED_HANDLER_MODULES = {
    RuleType.movie_watched_cleanup: movie_watched,
    RuleType.series_watched_cleanup: series_watched,
}


async def preview_watched_status(db: AsyncSession) -> dict:
    query = select(Rule).where(Rule.enabled == True, Rule.rule_type.in_(_WATCHED_RULE_TYPES))  # noqa: E712
    rules = list((await db.execute(query)).scalars().all())

    ctx = RuleContext(db)
    approaching: list[dict] = []
    exempt: list[dict] = []

    for rule in rules:
        handler_module = _WATCHED_HANDLER_MODULES[rule.rule_type]
        try:
            result = await handler_module.evaluate(db, None, rule, ctx, dry_run=True)
        except IntegrationError:
            continue
        for item in result.items:
            if item["status"] == "approaching":
                approaching.append(item)
            else:
                exempt.append(item)

    approaching.sort(key=lambda i: i["hours_remaining"])
    exempt.sort(key=lambda i: i["watched_at"] or "", reverse=True)

    return {"approaching": approaching, "exempt": exempt}
