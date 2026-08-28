from datetime import datetime, timedelta, timezone

from app.db.models import ThresholdUnit
from app.rules.thresholds import time_until_threshold


def test_time_until_threshold_returns_none_for_no_reference():
    assert time_until_threshold(None, 30, ThresholdUnit.days) is None


def test_time_until_threshold_returns_positive_remaining_time():
    watched_5_days_ago = datetime.now(timezone.utc) - timedelta(days=5)
    remaining = time_until_threshold(watched_5_days_ago, 30, ThresholdUnit.days)
    # threshold is 30 days, 5 have passed - about 25 days should remain
    assert timedelta(days=24, hours=23) < remaining < timedelta(days=25, hours=1)


def test_time_until_threshold_floors_at_zero_when_already_past():
    watched_45_days_ago = datetime.now(timezone.utc) - timedelta(days=45)
    remaining = time_until_threshold(watched_45_days_ago, 30, ThresholdUnit.days)
    assert remaining == timedelta(0)
