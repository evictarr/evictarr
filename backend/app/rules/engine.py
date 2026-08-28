import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EventLevel, Rule, RuleType, Run, RunStatus, RunType
from app.integrations.base_client import IntegrationError
from app.notifications.dispatcher import notify_run_summary
from app.rules import movie_watched, series_watched, stale_request
from app.rules.base import log_event
from app.rules.context import RuleContext

logger = logging.getLogger(__name__)

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


_PREVIEW_CACHE_TTL_SECONDS = 60
_PREVIEW_RESULT_LIMIT = 24
_preview_cache: dict | None = None
_preview_cache_at: datetime | None = None


async def preview_watched_status(db: AsyncSession) -> dict:
    """Live preview of items approaching cleanup or exempted from it, for the
    Dashboard. This is a *threshold* preview, not a deletion guarantee - an
    item can show here and still never be staged by a real scan (e.g. no
    TMDB/TVDB id, or missing from Radarr/Sonarr - checks the real scan makes
    but this preview doesn't itemize). Items without a resolvable
    jellyfin_item_id (e.g. pre-existing pending-deletion rows staged before
    that field was added, or anything from stale_request rules) show a
    placeholder instead of a poster, by design.

    Cached for _PREVIEW_CACHE_TTL_SECONDS since this walks the entire
    Jellyfin/Radarr/Sonarr/Seerr library per enabled watched rule - cheap
    enough for one dashboard load, not cheap enough for every render. Also
    capped to _PREVIEW_RESULT_LIMIT items per list after sorting, so a large
    library doesn't return (or render) hundreds of poster cards at once.
    """
    global _preview_cache, _preview_cache_at
    now = datetime.now(timezone.utc)
    if _preview_cache is not None and _preview_cache_at is not None:
        if (now - _preview_cache_at).total_seconds() < _PREVIEW_CACHE_TTL_SECONDS:
            return _preview_cache

    query = select(Rule).where(Rule.enabled == True, Rule.rule_type.in_(_WATCHED_RULE_TYPES))  # noqa: E712
    rules = list((await db.execute(query)).scalars().all())

    ctx = RuleContext(db)
    approaching: list[dict] = []
    exempt: list[dict] = []

    for rule in rules:
        handler_module = _WATCHED_HANDLER_MODULES[rule.rule_type]
        try:
            result = await handler_module.evaluate(db, None, rule, ctx, dry_run=True)
        except IntegrationError as exc:
            logger.warning("skipping rule %s in watched-status preview: %s", rule.id, exc)
            continue
        for item in result.items:
            if item["status"] == "approaching":
                approaching.append(item)
            else:
                exempt.append(item)

    approaching.sort(key=lambda i: i["hours_remaining"])
    exempt.sort(key=lambda i: i["watched_at"] or "", reverse=True)

    preview = {
        "approaching": approaching[:_PREVIEW_RESULT_LIMIT],
        "exempt": exempt[:_PREVIEW_RESULT_LIMIT],
    }
    _preview_cache = preview
    _preview_cache_at = now
    return preview
