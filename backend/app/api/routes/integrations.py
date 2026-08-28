from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.integrations import (
    IntegrationOut,
    IntegrationUpdateRequest,
    JellyfinUserOut,
    TestConnectionResponse,
)
from app.auth.dependencies import get_current_user
from app.db.base import get_db
from app.db.models import ServiceName
from app.integrations import service as integration_service
from app.integrations.base_client import IntegrationError

router = APIRouter(prefix="/api/integrations", tags=["integrations"], dependencies=[Depends(get_current_user)])


def _to_out(integration) -> IntegrationOut:
    return IntegrationOut(
        service=integration.service,
        base_url=integration.base_url,
        has_api_key=bool(integration.api_key_encrypted),
        extra_config=integration.extra_config,
        enabled=integration.enabled,
        last_test_status=integration.last_test_status,
        last_test_at=integration.last_test_at,
        last_test_detail=integration.last_test_detail,
    )


@router.get("", response_model=list[IntegrationOut])
async def list_integrations(db: AsyncSession = Depends(get_db)):
    integrations = await integration_service.list_integrations(db)
    return [_to_out(i) for i in integrations]


@router.put("/{service}", response_model=IntegrationOut)
async def update_integration(service: ServiceName, payload: IntegrationUpdateRequest, db: AsyncSession = Depends(get_db)):
    integration = await integration_service.update_integration(
        db, service, payload.base_url, payload.api_key, payload.extra_config, payload.enabled
    )
    return _to_out(integration)


@router.post("/{service}/test", response_model=TestConnectionResponse)
async def test_integration(service: ServiceName, db: AsyncSession = Depends(get_db)):
    ok, detail = await integration_service.test_integration(db, service)
    return TestConnectionResponse(ok=ok, detail=detail)


@router.get("/jellyfin/users", response_model=list[JellyfinUserOut])
async def list_jellyfin_users(db: AsyncSession = Depends(get_db)):
    integration = await integration_service.get_integration(db, ServiceName.jellyfin)
    if integration is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Jellyfin is not configured")
    try:
        client = integration_service.build_client(integration)
        users = await client.list_users()
    except IntegrationError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return [JellyfinUserOut(**u) for u in users]
