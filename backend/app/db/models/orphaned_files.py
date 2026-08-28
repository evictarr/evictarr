from datetime import datetime
from enum import Enum

from sqlalchemy import BigInteger, DateTime, Enum as SAEnum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LibraryContext(str, Enum):
    movies = "movies"
    tv = "tv"


class OrphanedStatus(str, Enum):
    open = "open"
    cleared = "cleared"


class OrphanedFile(Base):
    """Read-only report of files on disk that Radarr/Sonarr no longer track.
    Never feeds the deletion pipeline - clearing just marks it reviewed."""

    __tablename__ = "orphaned_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    path: Mapped[str] = mapped_column(String, unique=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    service_context: Mapped[LibraryContext] = mapped_column(SAEnum(LibraryContext, name="library_context"))
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status: Mapped[OrphanedStatus] = mapped_column(SAEnum(OrphanedStatus, name="orphaned_status"), default=OrphanedStatus.open)
    cleared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
