from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EventLevel, PendingMediaType, Rule, ServiceName, SeriesGranularity
from app.deletions.queue_service import stage
from app.integrations.jellyfin_client import is_favorite, is_played, parse_last_played, tvdb_id
from app.integrations.seerr_client import media_tvdb_id
from app.integrations.sonarr_client import find_by_tvdb_id
from app.rules.base import RuleResult, log_event
from app.rules.context import RuleContext
from app.rules.thresholds import is_past_threshold


async def evaluate(db: AsyncSession, run_id: int, rule: Rule, ctx: RuleContext) -> RuleResult:
    jellyfin = await ctx.client(ServiceName.jellyfin)
    user_id = await ctx.jellyfin_user_id()
    seerr = await ctx.client(ServiceName.seerr)
    sonarr = await ctx.client(ServiceName.sonarr)

    series_list = await jellyfin.get_series(user_id)
    sonarr_series = await sonarr.get_series()
    seerr_requests = await seerr.list_requests("available")

    result = RuleResult()

    if rule.granularity == SeriesGranularity.season:
        for series_item in series_list:
            tvdb = tvdb_id(series_item)
            series_name = series_item.get("Name", "Unknown")
            series_favorite = is_favorite(series_item)
            seasons = await jellyfin.get_seasons(user_id, series_item["Id"])

            for season in seasons:
                result.scanned += 1
                if not is_played(season):
                    continue
                if not is_past_threshold(parse_last_played(season), rule.threshold_value, rule.threshold_unit):
                    continue

                season_number = season.get("IndexNumber")
                title = f"{series_name} - Season {season_number}"

                if rule.exempt_favorite and (series_favorite or is_favorite(season)):
                    await log_event(db, run_id, rule.id, EventLevel.skip, title, "favorited")
                    result.skipped += 1
                    continue

                if not tvdb:
                    await log_event(db, run_id, rule.id, EventLevel.error, title, "Jellyfin series has no TVDB id")
                    result.skipped += 1
                    continue

                sonarr_entry = find_by_tvdb_id(sonarr_series, tvdb)
                if sonarr_entry is None:
                    await log_event(db, run_id, rule.id, EventLevel.error, title, "series not found in Sonarr")
                    result.skipped += 1
                    continue

                seerr_request = next((r for r in seerr_requests if media_tvdb_id(r) == tvdb), None)
                external_ids = {
                    "media_type": "season",
                    "tvdb_id": tvdb,
                    "sonarr_series_id": sonarr_entry["id"],
                    "season_number": season_number,
                    "seerr_request_id": seerr_request["id"] if seerr_request else None,
                }
                await log_event(db, run_id, rule.id, EventLevel.match, title, "watched past threshold", external_ids)
                await stage(db, rule.id, PendingMediaType.season, title, external_ids, f"season:{tvdb}:{season_number}")
                result.matched += 1
        return result

    # granularity == series: the whole show, evaluated as one unit
    for item in series_list:
        result.scanned += 1
        if not is_played(item):
            continue
        if not is_past_threshold(parse_last_played(item), rule.threshold_value, rule.threshold_unit):
            continue

        title = item.get("Name", "Unknown")
        tvdb = tvdb_id(item)

        if rule.exempt_favorite and is_favorite(item):
            await log_event(db, run_id, rule.id, EventLevel.skip, title, "favorited")
            result.skipped += 1
            continue

        if not tvdb:
            await log_event(db, run_id, rule.id, EventLevel.error, title, "Jellyfin item has no TVDB id")
            result.skipped += 1
            continue

        sonarr_entry = find_by_tvdb_id(sonarr_series, tvdb)
        if sonarr_entry is None:
            await log_event(db, run_id, rule.id, EventLevel.error, title, "not found in Sonarr")
            result.skipped += 1
            continue

        seerr_request = next((r for r in seerr_requests if media_tvdb_id(r) == tvdb), None)
        external_ids = {
            "media_type": "series",
            "tvdb_id": tvdb,
            "sonarr_series_id": sonarr_entry["id"],
            "seerr_request_id": seerr_request["id"] if seerr_request else None,
        }
        await log_event(db, run_id, rule.id, EventLevel.match, title, "watched past threshold", external_ids)
        await stage(db, rule.id, PendingMediaType.series, title, external_ids, f"series:{tvdb}")
        result.matched += 1

    return result
