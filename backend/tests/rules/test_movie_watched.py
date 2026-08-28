from datetime import datetime, timedelta, timezone

from app.db.models import Rule, RuleType, ServiceName, ThresholdUnit
from app.rules import movie_watched


class FakeJellyfin:
    def __init__(self, movies):
        self._movies = movies

    async def get_movies(self, user_id):
        return self._movies


class FakeRadarr:
    def __init__(self, movies):
        self._movies = movies

    async def get_movies(self):
        return self._movies


class FakeSeerr:
    async def list_requests(self, status):
        return []


class FakeContext:
    def __init__(self, jellyfin, radarr):
        self._clients = {ServiceName.jellyfin: jellyfin, ServiceName.radarr: radarr, ServiceName.seerr: FakeSeerr()}

    async def client(self, service):
        return self._clients[service]

    async def jellyfin_user_id(self):
        return "user-1"


def _movie_item(name, days_ago, favorite=False, tmdb="123"):
    played_date = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat().replace("+00:00", "Z")
    return {
        "Name": name,
        "Id": f"jf-{name}",
        "ProviderIds": {"Tmdb": tmdb},
        "UserData": {"Played": True, "LastPlayedDate": played_date, "IsFavorite": favorite},
    }


def _rule(threshold_days=30):
    return Rule(
        id=1,
        name="Movies after 30 days",
        rule_type=RuleType.movie_watched_cleanup,
        enabled=True,
        threshold_value=threshold_days,
        threshold_unit=ThresholdUnit.days,
        exempt_favorite=True,
    )


async def test_dry_run_reports_approaching_item_not_yet_past_threshold():
    movie = _movie_item("Recent Movie", days_ago=5)
    ctx = FakeContext(FakeJellyfin([movie]), FakeRadarr([{"id": 1, "tmdbId": "123"}]))

    result = await movie_watched.evaluate(None, None, _rule(threshold_days=30), ctx, dry_run=True)

    assert len(result.items) == 1
    item = result.items[0]
    assert item["status"] == "approaching"
    assert item["title"] == "Recent Movie"
    assert item["media_type"] == "movie"
    assert item["jellyfin_item_id"] == "jf-Recent Movie"
    assert item["hours_remaining"] > 0


async def test_dry_run_reports_exempt_item_past_threshold_and_favorited():
    movie = _movie_item("Old Favorite", days_ago=45, favorite=True)
    ctx = FakeContext(FakeJellyfin([movie]), FakeRadarr([{"id": 1, "tmdbId": "123"}]))

    result = await movie_watched.evaluate(None, None, _rule(threshold_days=30), ctx, dry_run=True)

    assert len(result.items) == 1
    item = result.items[0]
    assert item["status"] == "exempt"
    assert item["hours_remaining"] is None


async def test_dry_run_never_writes_to_db_for_matched_item():
    # db=None below: if dry_run mode ever called stage()/log_event() (both
    # of which call db.add(...)), this would crash with an AttributeError
    # on None - passing None is itself part of the assertion.
    movie = _movie_item("Past Threshold", days_ago=45, favorite=False)
    ctx = FakeContext(FakeJellyfin([movie]), FakeRadarr([{"id": 1, "tmdbId": "123"}]))

    result = await movie_watched.evaluate(None, None, _rule(threshold_days=30), ctx, dry_run=True)

    # Matched (past threshold, not exempt) - counted, but not itemized: a
    # real scan stages it immediately, so it belongs to pending-deletions,
    # not the dashboard's own preview.
    assert result.matched == 1
    assert result.items == []


async def test_real_scan_behavior_is_unchanged_when_dry_run_is_false():
    movie = _movie_item("Recent Movie", days_ago=5)
    ctx = FakeContext(FakeJellyfin([movie]), FakeRadarr([{"id": 1, "tmdbId": "123"}]))

    # db=None: the item is below threshold, so evaluate() continues past
    # it without ever touching db - same as before this change.
    result = await movie_watched.evaluate(None, None, _rule(threshold_days=30), ctx)

    assert result.items == []
    assert result.matched == 0
    assert result.scanned == 1
