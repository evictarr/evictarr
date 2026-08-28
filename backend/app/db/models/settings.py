from datetime import datetime, time

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Time, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AppSettings(Base):
    """Singleton settings row (id always 1)."""

    __tablename__ = "app_settings"
    __table_args__ = (CheckConstraint("id = 1", name="app_settings_singleton"),)

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    scheduler_time: Mapped[time] = mapped_column(Time, default=time(3, 30))
    timezone: Mapped[str] = mapped_column(String, default="UTC")
    default_grace_period_hours: Mapped[int] = mapped_column(Integer, default=24)
    executor_interval_minutes: Mapped[int] = mapped_column(Integer, default=15)
    log_retention_days: Mapped[int] = mapped_column(Integer, default=90)
    # "none" (no login required) or "basic" (username/password session login).
    # Not exposed through the generic /api/settings PUT - see
    # app/api/routes/auth.py's enable/disable endpoints.
    auth_method: Mapped[str] = mapped_column(String, default="none", server_default="none")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
