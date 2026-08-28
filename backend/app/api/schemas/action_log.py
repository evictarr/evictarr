from datetime import datetime

from pydantic import BaseModel

from app.db.models import OverallStatus, PendingMediaType, SystemStatus


class PendingDeletionSummary(BaseModel):
    id: int
    title: str
    media_type: PendingMediaType


class ActionLogOut(BaseModel):
    id: int
    pending_deletion: PendingDeletionSummary
    seerr_status: SystemStatus | None
    radarr_sonarr_status: SystemStatus | None
    disk_status: SystemStatus | None
    overall_status: OverallStatus
    error_detail: dict | None
    executed_at: datetime
