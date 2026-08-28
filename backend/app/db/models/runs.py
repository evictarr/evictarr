from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RunType(str, Enum):
    scheduled = "scheduled"
    manual = "manual"


class RunStatus(str, Enum):
    running = "running"
    completed = "completed"
    failed = "failed"


class EventLevel(str, Enum):
    match = "match"
    skip = "skip"
    error = "error"


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_type: Mapped[RunType] = mapped_column(SAEnum(RunType, name="run_type"))
    triggered_by: Mapped[str] = mapped_column(String)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[RunStatus] = mapped_column(SAEnum(RunStatus, name="run_status"), default=RunStatus.running)
    items_scanned: Mapped[int] = mapped_column(Integer, default=0)
    items_matched: Mapped[int] = mapped_column(Integer, default=0)
    items_skipped: Mapped[int] = mapped_column(Integer, default=0)


class RunEvent(Base):
    __tablename__ = "run_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"))
    rule_id: Mapped[int | None] = mapped_column(ForeignKey("rules.id"), nullable=True)
    level: Mapped[EventLevel] = mapped_column(SAEnum(EventLevel, name="event_level"))
    media_title: Mapped[str | None] = mapped_column(String, nullable=True)
    reason: Mapped[str | None] = mapped_column(String, nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
