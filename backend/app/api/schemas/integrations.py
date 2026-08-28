from datetime import datetime

from pydantic import BaseModel

from app.db.models import ServiceName, TestStatus


class IntegrationOut(BaseModel):
    service: ServiceName
    base_url: str | None
    has_api_key: bool
    extra_config: dict
    enabled: bool
    last_test_status: TestStatus
    last_test_at: datetime | None
    last_test_detail: str | None


class IntegrationUpdateRequest(BaseModel):
    base_url: str | None = None
    api_key: str | None = None  # omit to keep the existing stored key unchanged
    extra_config: dict = {}
    enabled: bool = True


class TestConnectionResponse(BaseModel):
    ok: bool
    detail: str


class JellyfinUserOut(BaseModel):
    id: str
    name: str
