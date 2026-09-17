from datetime import datetime, timedelta, timezone

from app.db.models import Rule, RuleType, Run, RunType, SeriesGranularity, ServiceName, ThresholdUnit
from app.rules import series_watched


class FakeJellyfin:
    def __init__(self, series, seasons_by_series_id=None, episodes_by_key=None):
        self._series = series
        self._seasons_by_series_id = seasons_by_series_id or {}
        # Keyed by season_id for season-granularity lookups, or by series_id
        # when get_episodes is called without a season_id (series
        # granularity) - mirrors the real client's get_episodes signature.
        self._episodes_by_key = episodes_by_key or {}

    async def get_series(self, user_id):
        return self._series

    async def get_seasons(self, user_id, series_id):
        return self._seasons_by_series_id.get(series_id, [])

    async def get_episodes(self, user_id, series_id, season_id=None):
        return self._episodes_by_key.get(season_id or series_id, [])


class FakeSonarr:
    def __init__(self, series):
        self._series = series

    async def get_series(self):
        return self._series


class FakeSeerr:
    def __init__(self, tv_details_by_tmdb=None):
        self._tv_details_by_tmdb = tv_details_by_tmdb or {}

    async def list_requests(self, status):
        return []

    async def get_tv_details(self, tmdb_id):
        return self._tv_details_by_tmdb[tmdb_id]


class FakeContext:
    def __init__(self, jellyfin, sonarr, seerr=None):
        self._clients = {
            ServiceName.jellyfin: jellyfin,
            ServiceName.sonarr: sonarr,
            ServiceName.seerr: seerr or FakeSeerr(),
        }

    async def client(self, service):
        return self._clients[service]

    async def jellyfin_user_id(self):
        return "user-1"


def _played_date(days_ago):
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat().replace("+00:00", "Z")


def _episode_item(days_ago, season_number=None):
    # Real Jellyfin stamps LastPlayedDate on the episode itself, never on
    # its parent Season/Series - see _season_item/_series_item below.
    # ParentIndexNumber is the episode's season number - only needed for
    # series-granularity (a season-granularity lookup already scopes
    # get_episodes to one season).
    item = {"UserData": {"Played": True, "LastPlayedDate": _played_date(days_ago)}}
    if season_number is not None:
        item["ParentIndexNumber"] = season_number
    return item


def _series_item(name, series_id, tvdb="456", tmdb=None, favorite=False, played=False, status=None):
    # Jellyfin's Series UserData never carries LastPlayedDate itself (only
    # Played/IsFavorite/UnplayedItemCount) - the rule has to derive a
    # watched-at timestamp from the series' episodes instead.
    provider_ids = {"Tvdb": tvdb}
    if tmdb is not None:
        provider_ids["Tmdb"] = tmdb
    item = {
        "Name": name,
        "Id": series_id,
        "ProviderIds": provider_ids,
        "UserData": {"Played": played, "IsFavorite": favorite},
    }
    if status is not None:
        item["Status"] = status
    return item


def _season_item(season_id, index_number, favorite=False):
    # Same deal as the series item: Played is accurate, LastPlayedDate is
    # never present on the season itself.
    return {
        "Id": season_id,
        "IndexNumber": index_number,
        "UserData": {"Played": True, "IsFavorite": favorite},
    }


def _rule(granularity, threshold_days=30):
    return Rule(
        id=1,
        name="Series after 30 days",
        rule_type=RuleType.series_watched_cleanup,
        enabled=True,
        threshold_value=threshold_days,
        threshold_unit=ThresholdUnit.days,
        granularity=granularity,
        exempt_favorite=True,
    )


async def test_dry_run_reports_approaching_season():
    series = _series_item("Some Show", "series-1")
    season = _season_item("season-1", index_number=2)
    jellyfin = FakeJellyfin(
        [series],
        seasons_by_series_id={"series-1": [season]},
        episodes_by_key={"season-1": [_episode_item(days_ago=5)]},
    )
    sonarr = FakeSonarr([{"id": 9, "tvdbId": "456"}])
    ctx = FakeContext(jellyfin, sonarr)

    result = await series_watched.evaluate(None, None, _rule(SeriesGranularity.season, 30), ctx, dry_run=True)

    assert len(result.items) == 1
    item = result.items[0]
    assert item["status"] == "approaching"
    assert item["media_type"] == "season"
    assert item["title"] == "Some Show - Season 2"
    assert item["jellyfin_item_id"] == "season-1"
    assert item["hours_remaining"] > 0


async def test_dry_run_reports_exempt_whole_series():
    series = _series_item("Favorited Show", "series-2", favorite=True, played=True)
    jellyfin = FakeJellyfin([series], episodes_by_key={"series-2": [_episode_item(days_ago=45)]})
    sonarr = FakeSonarr([{"id": 9, "tvdbId": "456"}])
    ctx = FakeContext(jellyfin, sonarr)

    result = await series_watched.evaluate(None, None, _rule(SeriesGranularity.series, 30), ctx, dry_run=True)

    assert len(result.items) == 1
    item = result.items[0]
    assert item["status"] == "exempt"
    assert item["media_type"] == "series"
    assert item["jellyfin_item_id"] == "series-2"


async def test_matched_season_is_staged_with_jellyfin_item_id(db_session):
    # Exercises the real (non-dry-run) path so stage() actually writes a
    # PendingDeletion row - confirms the external_ids fix this task makes
    # actually reaches the database, not just the dry-run preview dicts.
    from sqlalchemy import select

    from app.db.models import PendingDeletion

    series = _series_item("Some Show", "series-3")
    season = _season_item("season-3", index_number=1)
    jellyfin = FakeJellyfin(
        [series],
        seasons_by_series_id={"series-3": [season]},
        episodes_by_key={"season-3": [_episode_item(days_ago=45)]},
    )
    sonarr = FakeSonarr([{"id": 9, "tvdbId": "456"}])
    ctx = FakeContext(jellyfin, sonarr)
    rule = _rule(SeriesGranularity.season, 30)
    db_session.add(rule)
    await db_session.commit()
    await db_session.refresh(rule)

    run = Run(run_type=RunType.manual, triggered_by="test")
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)

    result = await series_watched.evaluate(db_session, run.id, rule, ctx)

    assert result.matched == 1
    staged = (await db_session.execute(select(PendingDeletion))).scalar_one()
    assert staged.external_ids["jellyfin_item_id"] == "season-3"


async def test_played_season_with_no_reachable_episodes_is_treated_as_not_due():
    # A season can be Played=true (Jellyfin's own aggregate) while its
    # episodes are temporarily unavailable to the API (e.g. a stale cache
    # entry) - watched_at then can't be determined, so the rule must treat
    # it the same as "not yet due" rather than crash or wrongly match.
    series = _series_item("Some Show", "series-4")
    season = _season_item("season-4", index_number=1)
    jellyfin = FakeJellyfin([series], seasons_by_series_id={"series-4": [season]}, episodes_by_key={})
    sonarr = FakeSonarr([{"id": 9, "tvdbId": "456"}])
    ctx = FakeContext(jellyfin, sonarr)

    result = await series_watched.evaluate(None, None, _rule(SeriesGranularity.season, 30), ctx, dry_run=True)

    assert result.items == []
    assert result.matched == 0


async def test_latest_season_of_continuing_show_is_not_matched_while_still_airing():
    # The Ted Lasso bug: Jellyfin marks a season "Played" once every episode
    # it currently has is watched, even when the show ("Status": "Continuing")
    # has more episodes coming. Seerr says the season should have 12
    # episodes; only 7 have been downloaded and watched so far.
    series = _series_item("Ted Lasso", "series-5", tmdb="97546", status="Continuing")
    season = _season_item("season-5", index_number=4)
    jellyfin = FakeJellyfin(
        [series],
        seasons_by_series_id={"series-5": [season]},
        episodes_by_key={"season-5": [_episode_item(days_ago=45) for _ in range(7)]},
    )
    sonarr = FakeSonarr([{"id": 9, "tvdbId": "456"}])
    seerr = FakeSeerr(tv_details_by_tmdb={"97546": {"seasons": [{"seasonNumber": 4, "episodeCount": 12}]}})
    ctx = FakeContext(jellyfin, sonarr, seerr)

    result = await series_watched.evaluate(None, None, _rule(SeriesGranularity.season, 30), ctx, dry_run=True)

    assert result.matched == 0
    assert result.skipped == 1
    assert result.items == []


async def test_latest_season_of_continuing_show_matches_once_fully_released():
    # Same show, but all 12 episodes Seerr expects for the season have now
    # been downloaded and watched - the season really is complete.
    series = _series_item("Ted Lasso", "series-6", tmdb="97546", status="Continuing")
    season = _season_item("season-6", index_number=4)
    jellyfin = FakeJellyfin(
        [series],
        seasons_by_series_id={"series-6": [season]},
        episodes_by_key={"season-6": [_episode_item(days_ago=45) for _ in range(12)]},
    )
    sonarr = FakeSonarr([{"id": 9, "tvdbId": "456"}])
    seerr = FakeSeerr(tv_details_by_tmdb={"97546": {"seasons": [{"seasonNumber": 4, "episodeCount": 12}]}})
    ctx = FakeContext(jellyfin, sonarr, seerr)

    result = await series_watched.evaluate(None, None, _rule(SeriesGranularity.season, 30), ctx, dry_run=True)

    assert result.matched == 1
    assert result.skipped == 0


async def test_only_the_latest_season_of_a_continuing_show_is_gated():
    # A finished earlier season must still be cleaned up on schedule even
    # while the show's newest season is ongoing - only the newest season
    # gets the extra completeness check.
    series = _series_item("Some Show", "series-7", tmdb="111", status="Continuing")
    season_1 = _season_item("season-7a", index_number=1)
    season_2 = _season_item("season-7b", index_number=2)
    jellyfin = FakeJellyfin(
        [series],
        seasons_by_series_id={"series-7": [season_1, season_2]},
        episodes_by_key={
            "season-7a": [_episode_item(days_ago=45) for _ in range(10)],
            "season-7b": [_episode_item(days_ago=45) for _ in range(3)],
        },
    )
    sonarr = FakeSonarr([{"id": 9, "tvdbId": "456"}])
    seerr = FakeSeerr(
        tv_details_by_tmdb={"111": {"seasons": [{"seasonNumber": 1, "episodeCount": 10}, {"seasonNumber": 2, "episodeCount": 8}]}}
    )
    ctx = FakeContext(jellyfin, sonarr, seerr)

    result = await series_watched.evaluate(None, None, _rule(SeriesGranularity.season, 30), ctx, dry_run=True)

    assert result.matched == 1  # season 1 only
    assert result.skipped == 1  # season 2, still airing


async def test_continuing_show_with_no_tmdb_id_does_not_match_latest_season():
    # Without a TMDB id there's no way to ask Seerr how many episodes the
    # season should have - fail closed rather than risk deleting an
    # ongoing season.
    series = _series_item("Some Show", "series-8", status="Continuing")
    season = _season_item("season-8", index_number=1)
    jellyfin = FakeJellyfin(
        [series],
        seasons_by_series_id={"series-8": [season]},
        episodes_by_key={"season-8": [_episode_item(days_ago=45)]},
    )
    sonarr = FakeSonarr([{"id": 9, "tvdbId": "456"}])
    ctx = FakeContext(jellyfin, sonarr)

    result = await series_watched.evaluate(None, None, _rule(SeriesGranularity.season, 30), ctx, dry_run=True)

    assert result.matched == 0
    assert result.skipped == 1


async def test_series_granularity_does_not_delete_whole_show_while_newest_season_airs():
    # The whole-series rule has the exact same problem as the season rule -
    # it would delete every season, including the finished ones, while the
    # newest season is still catching up on downloads.
    series = _series_item("Ted Lasso", "series-9", tmdb="97546", played=True, status="Continuing")
    episodes = [_episode_item(days_ago=45, season_number=1) for _ in range(10)]
    episodes += [_episode_item(days_ago=45, season_number=4) for _ in range(7)]
    jellyfin = FakeJellyfin(
        [series],
        seasons_by_series_id={
            "series-9": [_season_item("s1", index_number=1), _season_item("s4", index_number=4)]
        },
        episodes_by_key={"series-9": episodes},
    )
    sonarr = FakeSonarr([{"id": 9, "tvdbId": "456"}])
    seerr = FakeSeerr(tv_details_by_tmdb={"97546": {"seasons": [{"seasonNumber": 4, "episodeCount": 12}]}})
    ctx = FakeContext(jellyfin, sonarr, seerr)

    result = await series_watched.evaluate(None, None, _rule(SeriesGranularity.series, 30), ctx, dry_run=True)

    assert result.matched == 0
    assert result.skipped == 1


async def test_series_granularity_matches_once_newest_season_is_fully_released():
    series = _series_item("Ted Lasso", "series-10", tmdb="97546", played=True, status="Continuing")
    episodes = [_episode_item(days_ago=45, season_number=1) for _ in range(10)]
    episodes += [_episode_item(days_ago=45, season_number=4) for _ in range(12)]
    jellyfin = FakeJellyfin(
        [series],
        seasons_by_series_id={
            "series-10": [_season_item("s1", index_number=1), _season_item("s4", index_number=4)]
        },
        episodes_by_key={"series-10": episodes},
    )
    sonarr = FakeSonarr([{"id": 9, "tvdbId": "456"}])
    seerr = FakeSeerr(tv_details_by_tmdb={"97546": {"seasons": [{"seasonNumber": 4, "episodeCount": 12}]}})
    ctx = FakeContext(jellyfin, sonarr, seerr)

    result = await series_watched.evaluate(None, None, _rule(SeriesGranularity.series, 30), ctx, dry_run=True)

    assert result.matched == 1
    assert result.skipped == 0
