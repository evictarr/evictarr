from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.base import get_db
from app.db.models import ServiceName
from app.integrations import service as integration_service
from app.integrations.base_client import IntegrationError

router = APIRouter(prefix="/api/media", tags=["media"], dependencies=[Depends(get_current_user)])


@router.get("/poster/{jellyfin_item_id}")
async def get_poster(jellyfin_item_id: str, db: AsyncSession = Depends(get_db)):
    integration = await integration_service.get_integration(db, ServiceName.jellyfin)
    if integration is None or not integration.enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Jellyfin is not configured")
    try:
        client = integration_service.build_client(integration)
        image = await client.get(f"/Items/{jellyfin_item_id}/Images/Primary")
    except IntegrationError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    content_type = image.headers.get("content-type", "image/jpeg")
    return Response(content=image.content, media_type=content_type, headers={"Cache-Control": "public, max-age=86400"})
