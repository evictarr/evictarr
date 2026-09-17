from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EventLevel, PendingMediaType, Rule, ServiceName, SeriesGranularity
from app.deletions.queue_service import stage
from app.integrations.base_client import IntegrationError
from app.integrations.jellyfin_client import (
    is_favorite,
    is_played,
    latest_played_at,
    series_status,
    tmdb_id,
    tvdb_id,
)
from app.integrations.seerr_client import media_tvdb_id, season_episode_count
from app.integrations.sonarr_client import find_by_tvdb_id
from app.rules.base import RuleResult, log_event
from app.rules.context import RuleContext
from app.rules.thresholds import is_past_threshold, time_until_threshold


async def _last_season_still_airing(seerr, tmdb: str | None, season_number: int, available_episodes: int) -> bool:
    """Whether the final season of a still-"Continuing" show has more
    episodes coming that Jellyfin doesn't have yet.

    Jellyfin marks a season "Played" as soon as every episode it currently
    holds has been watched - it has no idea whether the season itself is
    finished airing. Seerr proxies TMDB's per-season episode count, which is
    the only signal available for "watched everything downloaded so far" vs
    "watched everything there will ever be". Anything that can't be verified
    (no TMDB id, Seerr unreachable, season not found) is treated as still
    airing, so a genuinely-ongoing final season is never matched by mistake.
    """
    if not tmdb:
        return True
    try:
        tv_details = await seerr.get_tv_details(tmdb)
    except IntegrationError:
        return True
    expected = season_episode_count(tv_details, season_number)
    if expected is None:
        return True
    return available_episodes < expected


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
            tmdb = tmdb_id(series_item)
            series_name = series_item.get("Name", "Unknown")
            series_favorite = is_favorite(series_item)
            series_continuing = series_status(series_item) == "Continuing"
            seasons = await jellyfin.get_seasons(user_id, series_item["Id"])
            last_season_number = max(
                (s.get("IndexNumber") for s in seasons if isinstance(s.get("IndexNumber"), int)),
                default=None,
            )

            for season in seasons:
                result.scanned += 1
                if not is_played(season):
                    continue

                season_number = season.get("IndexNumber")
                title = f"{series_name} - Season {season_number}"
                # Jellyfin never sets LastPlayedDate on the season item
                # itself - only on its episodes - so it has to be derived
                # from them instead of read off `season` directly.
                episodes = await jellyfin.get_episodes(user_id, series_item["Id"], season["Id"])
                watched_at = latest_played_at(episodes)

                # A still-airing show's latest season is "Played" the moment
                # its downloaded episodes are all watched, even though more
                # episodes are coming next week - only check this for the
                # newest season of a show Jellyfin itself still calls
                # "Continuing", so already-ended shows (the overwhelming
                # majority) skip the extra Seerr lookup entirely.
                if (
                    series_continuing
                    and season_number is not None
                    and season_number == last_season_number
                    and await _last_season_still_airing(seerr, tmdb, season_number, len(episodes))
                ):
                    if not dry_run:
                        await log_event(
                            db, run_id, rule.id, EventLevel.skip, title, "latest season is still airing"
                        )
                    result.skipped += 1
                    continue

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
        # Same deal as the season branch above: Series items don't carry
        # their own LastPlayedDate, so pull it from the episodes.
        episodes = await jellyfin.get_episodes(user_id, item["Id"])
        watched_at = latest_played_at(episodes)

        # Same "Continuing" show, still-airing newest season problem as the
        # season branch above - here it would delete the *entire* series,
        # not just one season, so it's checked the same way: is the show's
        # newest season (per Jellyfin's own seasons list) fully released yet?
        if series_status(item) == "Continuing":
            seasons = await jellyfin.get_seasons(user_id, item["Id"])
            last_season_number = max(
                (s.get("IndexNumber") for s in seasons if isinstance(s.get("IndexNumber"), int)),
                default=None,
            )
            if last_season_number is not None:
                episodes_in_last_season = sum(1 for e in episodes if e.get("ParentIndexNumber") == last_season_number)
                if await _last_season_still_airing(seerr, tmdb_id(item), last_season_number, episodes_in_last_season):
                    if not dry_run:
                        await log_event(db, run_id, rule.id, EventLevel.skip, title, "latest season is still airing")
                    result.skipped += 1
                    continue

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
