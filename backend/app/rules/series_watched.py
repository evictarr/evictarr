from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EventLevel, PendingMediaType, Rule, ServiceName, SeriesGranularity
from app.deletions.queue_service import stage
from app.integrations.jellyfin_client import is_favorite, is_played, parse_last_played, tvdb_id
from app.integrations.seerr_client import media_tvdb_id
from app.integrations.sonarr_client import find_by_tvdb_id
from app.rules.base import RuleResult, log_event
from app.rules.context import RuleContext
from app.rules.thresholds import is_past_threshold, time_until_threshold


async def evaluate(
    db: AsyncSession,
    run_id: int | None,
    rule: Rule,
    ctx: RuleContext,
    dry_run: bool = False,
) -> RuleResult:
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

                season_number = season.get("IndexNumber")
                title = f"{series_name} - Season {season_number}"
                watched_at = parse_last_played(season)

                if not is_past_threshold(watched_at, rule.threshold_value, rule.threshold_unit):
                    if dry_run and watched_at is not None:
                        result.items.append(
                            {
                                "title": title,
                                "media_type": "season",
                                "jellyfin_item_id": season.get("Id"),
                                "watched_at": watched_at.isoformat(),
                                "rule_id": rule.id,
                                "rule_name": rule.name,
                                "status": "approaching",
                                "threshold_value": rule.threshold_value,
                                "threshold_unit": rule.threshold_unit.value,
                                "hours_remaining": time_until_threshold(
                                    watched_at, rule.threshold_value, rule.threshold_unit
                                ).total_seconds()
                                / 3600,
                            }
                        )
                    continue

                if rule.exempt_favorite and (series_favorite or is_favorite(season)):
                    if dry_run:
                        result.items.append(
                            {
                                "title": title,
                                "media_type": "season",
                                "jellyfin_item_id": season.get("Id"),
                                "watched_at": watched_at.isoformat() if watched_at else None,
                                "rule_id": rule.id,
                                "rule_name": rule.name,
                                "status": "exempt",
                                "threshold_value": rule.threshold_value,
                                "threshold_unit": rule.threshold_unit.value,
                                "hours_remaining": None,
                            }
                        )
                    else:
                        await log_event(db, run_id, rule.id, EventLevel.skip, title, "favorited")
                    result.skipped += 1
                    continue

                if not tvdb:
                    if not dry_run:
                        await log_event(db, run_id, rule.id, EventLevel.error, title, "Jellyfin series has no TVDB id")
                    result.skipped += 1
                    continue

                sonarr_entry = find_by_tvdb_id(sonarr_series, tvdb)
                if sonarr_entry is None:
                    if not dry_run:
                        await log_event(db, run_id, rule.id, EventLevel.error, title, "series not found in Sonarr")
                    result.skipped += 1
                    continue

                seerr_request = next((r for r in seerr_requests if media_tvdb_id(r) == tvdb), None)
                external_ids = {
                    "media_type": "season",
                    "tvdb_id": tvdb,
                    "jellyfin_item_id": season.get("Id"),
                    "sonarr_series_id": sonarr_entry["id"],
                    "season_number": season_number,
                    "seerr_request_id": seerr_request["id"] if seerr_request else None,
                }
                if dry_run:
                    result.matched += 1
                    continue
                await log_event(db, run_id, rule.id, EventLevel.match, title, "watched past threshold", external_ids)
                await stage(db, rule.id, PendingMediaType.season, title, external_ids, f"season:{tvdb}:{season_number}")
                result.matched += 1
        return result

    # granularity == series: the whole show, evaluated as one unit
    for item in series_list:
        result.scanned += 1
        if not is_played(item):
            continue

        title = item.get("Name", "Unknown")
        tvdb = tvdb_id(item)
        watched_at = parse_last_played(item)

        if not is_past_threshold(watched_at, rule.threshold_value, rule.threshold_unit):
            if dry_run and watched_at is not None:
                result.items.append(
                    {
                        "title": title,
                        "media_type": "series",
                        "jellyfin_item_id": item.get("Id"),
                        "watched_at": watched_at.isoformat(),
                        "rule_id": rule.id,
                        "rule_name": rule.name,
                        "status": "approaching",
                        "threshold_value": rule.threshold_value,
                        "threshold_unit": rule.threshold_unit.value,
                        "hours_remaining": time_until_threshold(
                            watched_at, rule.threshold_value, rule.threshold_unit
                        ).total_seconds()
                        / 3600,
                    }
                )
            continue

        if rule.exempt_favorite and is_favorite(item):
            if dry_run:
                result.items.append(
                    {
                        "title": title,
                        "media_type": "series",
                        "jellyfin_item_id": item.get("Id"),
                        "watched_at": watched_at.isoformat() if watched_at else None,
                        "rule_id": rule.id,
                        "rule_name": rule.name,
                        "status": "exempt",
                        "threshold_value": rule.threshold_value,
                        "threshold_unit": rule.threshold_unit.value,
                        "hours_remaining": None,
                    }
                )
            else:
                await log_event(db, run_id, rule.id, EventLevel.skip, title, "favorited")
            result.skipped += 1
            continue

        if not tvdb:
            if not dry_run:
                await log_event(db, run_id, rule.id, EventLevel.error, title, "Jellyfin item has no TVDB id")
            result.skipped += 1
            continue

        sonarr_entry = find_by_tvdb_id(sonarr_series, tvdb)
        if sonarr_entry is None:
            if not dry_run:
                await log_event(db, run_id, rule.id, EventLevel.error, title, "not found in Sonarr")
            result.skipped += 1
            continue

        seerr_request = next((r for r in seerr_requests if media_tvdb_id(r) == tvdb), None)
        external_ids = {
            "media_type": "series",
            "tvdb_id": tvdb,
            "jellyfin_item_id": item.get("Id"),
            "sonarr_series_id": sonarr_entry["id"],
            "seerr_request_id": seerr_request["id"] if seerr_request else None,
        }
        if dry_run:
            result.matched += 1
            continue
        await log_event(db, run_id, rule.id, EventLevel.match, title, "watched past threshold", external_ids)
        await stage(db, rule.id, PendingMediaType.series, title, external_ids, f"series:{tvdb}")
        result.matched += 1

    return result
