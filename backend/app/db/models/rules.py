from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RuleType(str, Enum):
    movie_watched_cleanup = "movie_watched_cleanup"
    series_watched_cleanup = "series_watched_cleanup"
    stale_request_cleanup = "stale_request_cleanup"
    orphaned_scan = "orphaned_scan"


class ThresholdUnit(str, Enum):
    hours = "hours"
    days = "days"
    weeks = "weeks"
    months = "months"
    years = "years"


class SeriesGranularity(str, Enum):
    series = "series"
    season = "season"


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)
    rule_type: Mapped[RuleType] = mapped_column(SAEnum(RuleType, name="rule_type"))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    threshold_value: Mapped[int] = mapped_column(Integer, default=30)
    threshold_unit: Mapped[ThresholdUnit] = mapped_column(
        SAEnum(ThresholdUnit, name="threshold_unit"), default=ThresholdUnit.days
    )
    granularity: Mapped[SeriesGranularity | None] = mapped_column(
        SAEnum(SeriesGranularity, name="series_granularity"), nullable=True
    )
    exempt_favorite: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
