from datetime import datetime

from pydantic import BaseModel

from app.db.models import PendingMediaType, PendingStatus


class PendingDeletionOut(BaseModel):
    id: int
    rule_id: int | None
    media_type: PendingMediaType
    title: str
    external_ids: dict
    staged_at: datetime
    grace_period_hours: int
    execute_after: datetime
    status: PendingStatus
    cancelled_at: datetime | None
    cancelled_reason: str | None


class CancelRequest(BaseModel):
    reason: str | None = None
