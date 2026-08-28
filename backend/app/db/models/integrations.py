from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SAEnum, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ServiceName(str, Enum):
    jellyfin = "jellyfin"
    seerr = "seerr"
    radarr = "radarr"
    sonarr = "sonarr"


class TestStatus(str, Enum):
    unknown = "unknown"
    ok = "ok"
    failed = "failed"


class Integration(Base):
    __tablename__ = "integrations"

    id: Mapped[int] = mapped_column(primary_key=True)
    service: Mapped[ServiceName] = mapped_column(SAEnum(ServiceName, name="service_name"), unique=True)
    base_url: Mapped[str | None] = mapped_column(String, nullable=True)
    api_key_encrypted: Mapped[str | None] = mapped_column(String, nullable=True)
    extra_config: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(default=False)
    last_test_status: Mapped[TestStatus] = mapped_column(
        SAEnum(TestStatus, name="test_status"), default=TestStatus.unknown
    )
    last_test_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_test_detail: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
