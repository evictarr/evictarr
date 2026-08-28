from datetime import datetime, timedelta, timezone

from app.db.models.rules import ThresholdUnit

# months/years are approximated - good enough for a cleanup threshold, not
# calendar-exact.
_UNIT_TO_HOURS = {
    ThresholdUnit.hours: 1,
    ThresholdUnit.days: 24,
    ThresholdUnit.weeks: 24 * 7,
    ThresholdUnit.months: 24 * 30,
    ThresholdUnit.years: 24 * 365,
}


def cutoff_datetime(threshold_value: int, threshold_unit: ThresholdUnit) -> datetime:
    hours = threshold_value * _UNIT_TO_HOURS[threshold_unit]
    return datetime.now(timezone.utc) - timedelta(hours=hours)


def is_past_threshold(reference: datetime | None, threshold_value: int, threshold_unit: ThresholdUnit) -> bool:
    if reference is None:
        return False
    return reference <= cutoff_datetime(threshold_value, threshold_unit)


def time_until_threshold(reference: datetime | None, threshold_value: int, threshold_unit: ThresholdUnit) -> timedelta | None:
    """How much longer until `reference` would satisfy is_past_threshold -
    None if there's no reference at all, timedelta(0) if it's already past."""
    if reference is None:
        return None
    remaining = reference - cutoff_datetime(threshold_value, threshold_unit)
    return remaining if remaining > timedelta(0) else timedelta(0)
