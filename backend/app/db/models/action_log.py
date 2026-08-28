from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SystemStatus(str, Enum):
    success = "success"
    failed = "failed"
    skipped = "skipped"


class OverallStatus(str, Enum):
    success = "success"
    partial_failure = "partial_failure"
    failed = "failed"


_system_status_enum = SAEnum(SystemStatus, name="system_status")


class ActionLog(Base):
    """One row per grace-period execution attempt - the audit trail of what
    was actually deleted, from where, and whether each system succeeded."""

    __tablename__ = "action_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    pending_deletion_id: Mapped[int] = mapped_column(ForeignKey("pending_deletions.id"))
    seerr_status: Mapped[SystemStatus | None] = mapped_column(_system_status_enum, nullable=True)
    radarr_sonarr_status: Mapped[SystemStatus | None] = mapped_column(_system_status_enum, nullable=True)
    disk_status: Mapped[SystemStatus | None] = mapped_column(_system_status_enum, nullable=True)
    overall_status: Mapped[OverallStatus] = mapped_column(SAEnum(OverallStatus, name="overall_status"))
    error_detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
