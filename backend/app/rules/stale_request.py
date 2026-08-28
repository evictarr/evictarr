from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EventLevel, PendingMediaType, Rule, ServiceName
from app.deletions.queue_service import stage
from app.integrations.jellyfin_client import is_favorite, play_count, tmdb_id, tvdb_id
from app.integrations.radarr_client import find_by_tmdb_id
from app.integrations.seerr_client import media_added_at, media_tmdb_id, media_tvdb_id, media_type
from app.integrations.sonarr_client import find_by_tvdb_id
from app.rules.base import RuleResult, log_event
from app.rules.context import RuleContext
from app.rules.thresholds import is_past_threshold


def _parse_added_at(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


async def evaluate(db: AsyncSession, run_id: int, rule: Rule, ctx: RuleContext) -> RuleResult:
    seerr = await ctx.client(ServiceName.seerr)
    jellyfin = await ctx.client(ServiceName.jellyfin)
    user_id = await ctx.jellyfin_user_id()
    radarr = await ctx.client(ServiceName.radarr)
    sonarr = await ctx.client(ServiceName.sonarr)

    requests = await seerr.list_requests("available")
    movies = await jellyfin.get_movies(user_id)
    series_list = await jellyfin.get_series(user_id)
    radarr_movies = await radarr.get_movies()
    sonarr_series = await sonarr.get_series()

    result = RuleResult()
    for request in requests:
        result.scanned += 1
        added_at = _parse_added_at(media_added_at(request))
        if not is_past_threshold(added_at, rule.threshold_value, rule.threshold_unit):
            continue

        mtype = media_type(request)
        if mtype == "movie":
            tmdb = media_tmdb_id(request)
            jf_item = next((m for m in movies if tmdb_id(m) == tmdb), None)
        else:
            tvdb = media_tvdb_id(request)
            jf_item = next((s for s in series_list if tvdb_id(s) == tvdb), None)

        if jf_item is None:
            await log_event(
                db, run_id, rule.id, EventLevel.error, f"Seerr request #{request['id']}", "not found in Jellyfin library"
            )
            result.skipped += 1
            continue

        # PlayCount aggregates episode plays for a series in Jellyfin - if it's
        # 0, nobody has ever watched anything from this request.
        if play_count(jf_item) > 0:
            continue

        title = jf_item.get("Name", "Unknown")
        if rule.exempt_favorite and is_favorite(jf_item):
            await log_event(db, run_id, rule.id, EventLevel.skip, title, "favorited")
            result.skipped += 1
            continue

        if mtype == "movie":
            radarr_movie = find_by_tmdb_id(radarr_movies, media_tmdb_id(request))
            if radarr_movie is None:
                await log_event(db, run_id, rule.id, EventLevel.error, title, "not found in Radarr")
                result.skipped += 1
                continue
            external_ids = {
                "media_type": "movie",
                "seerr_request_id": request["id"],
                "tmdb_id": media_tmdb_id(request),
                "radarr_movie_id": radarr_movie["id"],
            }
            dedupe_key = f"movie:{media_tmdb_id(request)}"
            pending_media_type = PendingMediaType.movie
        else:
            sonarr_entry = find_by_tvdb_id(sonarr_series, media_tvdb_id(request))
            if sonarr_entry is None:
                await log_event(db, run_id, rule.id, EventLevel.error, title, "not found in Sonarr")
                result.skipped += 1
                continue
            external_ids = {
                "media_type": "series",
                "seerr_request_id": request["id"],
                "tvdb_id": media_tvdb_id(request),
                "sonarr_series_id": sonarr_entry["id"],
            }
            dedupe_key = f"series:{media_tvdb_id(request)}"
            pending_media_type = PendingMediaType.series

        await log_event(db, run_id, rule.id, EventLevel.match, title, "never watched since it became available", external_ids)
        await stage(db, rule.id, pending_media_type, title, external_ids, dedupe_key)
        result.matched += 1

    return result
