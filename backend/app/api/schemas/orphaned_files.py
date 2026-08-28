from datetime import datetime

from pydantic import BaseModel

from app.db.models import LibraryContext, OrphanedStatus


class OrphanedFileOut(BaseModel):
    id: int
    path: str
    size_bytes: int
    service_context: LibraryContext
    detected_at: datetime
    status: OrphanedStatus
    cleared_at: datetime | None


class OrphanedScanResponse(BaseModel):
    found: int
