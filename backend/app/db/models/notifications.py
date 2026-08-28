from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NotificationProviderName(str, Enum):
    discord = "discord"
    telegram = "telegram"


class NotificationConfig(Base):
    __tablename__ = "notification_config"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[NotificationProviderName] = mapped_column(
        SAEnum(NotificationProviderName, name="notification_provider"), unique=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    notify_on_stage: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_on_execute: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_daily_summary: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
