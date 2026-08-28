from datetime import datetime

from pydantic import BaseModel

from app.db.models import EventLevel, RunStatus, RunType


class RunOut(BaseModel):
    id: int
    run_type: RunType
    triggered_by: str
    started_at: datetime
    finished_at: datetime | None
    status: RunStatus
    items_scanned: int
    items_matched: int
    items_skipped: int


class RunEventOut(BaseModel):
    id: int
    rule_id: int | None
    level: EventLevel
    media_title: str | None
    reason: str | None
    detail: dict | None
    created_at: datetime


class RunNowRequest(BaseModel):
    rule_ids: list[int] | None = None
