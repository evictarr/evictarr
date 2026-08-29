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
    async def list_requests(self, status):
        return []


class FakeContext:
    def __init__(self, jellyfin, sonarr):
        self._clients = {ServiceName.jellyfin: jellyfin, ServiceName.sonarr: sonarr, ServiceName.seerr: FakeSeerr()}

    async def client(self, service):
        return self._clients[service]

    async def jellyfin_user_id(self):
        return "user-1"


def _played_date(days_ago):
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat().replace("+00:00", "Z")


def _episode_item(days_ago):
    # Real Jellyfin stamps LastPlayedDate on the episode itself, never on
    # its parent Season/Series - see _season_item/_series_item below.
    return {"UserData": {"Played": True, "LastPlayedDate": _played_date(days_ago)}}


def _series_item(name, series_id, tvdb="456", favorite=False, played=False):
    # Jellyfin's Series UserData never carries LastPlayedDate itself (only
    # Played/IsFavorite/UnplayedItemCount) - the rule has to derive a
    # watched-at timestamp from the series' episodes instead.
    return {
        "Name": name,
        "Id": series_id,
        "ProviderIds": {"Tvdb": tvdb},
        "UserData": {"Played": played, "IsFavorite": favorite},
    }


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
