from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PendingMediaType(str, Enum):
    movie = "movie"
    series = "series"
    season = "season"


class PendingStatus(str, Enum):
    pending = "pending"
    cancelled = "cancelled"
    executing = "executing"
    completed = "completed"
    failed = "failed"


class PendingDeletion(Base):
    __tablename__ = "pending_deletions"

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[int | None] = mapped_column(ForeignKey("rules.id"), nullable=True)
    media_type: Mapped[PendingMediaType] = mapped_column(SAEnum(PendingMediaType, name="pending_media_type"))
    title: Mapped[str] = mapped_column(String)
    external_ids: Mapped[dict] = mapped_column(JSON, default=dict)
    # e.g. "movie:12345" or "season:6789:2" - used to avoid staging the same
    # underlying media twice while an active pending row already exists.
    dedupe_key: Mapped[str] = mapped_column(String, index=True)
    staged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    grace_period_hours: Mapped[int] = mapped_column(Integer)
    execute_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[PendingStatus] = mapped_column(SAEnum(PendingStatus, name="pending_status"), default=PendingStatus.pending)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_reason: Mapped[str | None] = mapped_column(String, nullable=True)
