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
