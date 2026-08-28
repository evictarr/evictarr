from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    """Single-user table. The CheckConstraint enforces id=1 so the app never
    accidentally grows a multi-user model it wasn't designed for."""

    __tablename__ = "users"
    __table_args__ = (CheckConstraint("id = 1", name="users_singleton"),)

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    username: Mapped[str] = mapped_column(String, unique=True)
    password_hash: Mapped[str] = mapped_column(String)
    mfa_enabled: Mapped[bool] = mapped_column(default=False)
    totp_secret_encrypted: Mapped[str | None] = mapped_column(String, nullable=True)
    mfa_enrolled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
