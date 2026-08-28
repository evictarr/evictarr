from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EventLevel, PendingMediaType, Rule, ServiceName
from app.deletions.queue_service import stage
from app.integrations.jellyfin_client import is_favorite, is_played, parse_last_played, tmdb_id
from app.integrations.radarr_client import find_by_tmdb_id
from app.integrations.seerr_client import media_tmdb_id
from app.rules.base import RuleResult, log_event
from app.rules.context import RuleContext
from app.rules.thresholds import is_past_threshold


async def evaluate(db: AsyncSession, run_id: int, rule: Rule, ctx: RuleContext) -> RuleResult:
    jellyfin = await ctx.client(ServiceName.jellyfin)
    user_id = await ctx.jellyfin_user_id()
    seerr = await ctx.client(ServiceName.seerr)
    radarr = await ctx.client(ServiceName.radarr)

    movies = await jellyfin.get_movies(user_id)
    radarr_movies = await radarr.get_movies()
    seerr_requests = await seerr.list_requests("available")

    result = RuleResult()
    for item in movies:
        result.scanned += 1
        if not is_played(item):
            continue
        if not is_past_threshold(parse_last_played(item), rule.threshold_value, rule.threshold_unit):
            continue

        title = item.get("Name", "Unknown")
        tmdb = tmdb_id(item)

        if rule.exempt_favorite and is_favorite(item):
            await log_event(db, run_id, rule.id, EventLevel.skip, title, "favorited")
            result.skipped += 1
            continue

        if not tmdb:
            await log_event(db, run_id, rule.id, EventLevel.error, title, "Jellyfin item has no TMDB id")
            result.skipped += 1
            continue

        radarr_movie = find_by_tmdb_id(radarr_movies, tmdb)
        if radarr_movie is None:
            await log_event(db, run_id, rule.id, EventLevel.error, title, "not found in Radarr")
            result.skipped += 1
            continue

        seerr_request = next((r for r in seerr_requests if media_tmdb_id(r) == tmdb), None)
        external_ids = {
            "media_type": "movie",
            "tmdb_id": tmdb,
            "jellyfin_item_id": item.get("Id"),
            "radarr_movie_id": radarr_movie["id"],
            "seerr_request_id": seerr_request["id"] if seerr_request else None,
        }
        await log_event(db, run_id, rule.id, EventLevel.match, title, "watched past threshold", external_ids)
        await stage(db, rule.id, PendingMediaType.movie, title, external_ids, f"movie:{tmdb}")
        result.matched += 1

    return result
