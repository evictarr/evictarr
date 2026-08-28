import re

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.base import get_db
from app.db.models import ServiceName
from app.integrations import service as integration_service
from app.integrations.base_client import IntegrationError

router = APIRouter(prefix="/api/media", tags=["media"], dependencies=[Depends(get_current_user)])

# Jellyfin item IDs are hex GUIDs, optionally with dashes. Rejecting anything
# else before it's interpolated into the outbound request path stops path/query
# injection (e.g. "?fields=Everything") and other malformed values that would
# otherwise reach httpx unvalidated. The charset restriction is what actually
# blocks injection (no "?", "/", "..", control chars, etc. can ever match);
# the length bound is just a sane upper cap - real Jellyfin GUIDs are 32-36
# chars, but the lower bound is kept permissive (1) rather than the stricter
# 8 so short ids stay valid.
_JELLYFIN_ITEM_ID_PATTERN = re.compile(r"^[0-9a-fA-F-]{1,40}$")

# Only ever relay actual image bytes to the browser - never trust the upstream
# Content-Type blindly, since a mislabeled response (e.g. JSON) would otherwise
# be served under a URL the frontend treats as always-safe image content.
_ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


@router.get("/poster/{jellyfin_item_id}")
async def get_poster(jellyfin_item_id: str, db: AsyncSession = Depends(get_db)):
    if not _JELLYFIN_ITEM_ID_PATTERN.fullmatch(jellyfin_item_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invalid item id")
    integration = await integration_service.get_integration(db, ServiceName.jellyfin)
    if integration is None or not integration.enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Jellyfin is not configured")
    try:
        client = integration_service.build_client(integration)
        image = await client.get(f"/Items/{jellyfin_item_id}/Images/Primary")
    except IntegrationError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Poster unavailable") from exc
    content_type = image.headers.get("content-type", "image/jpeg").split(";")[0].strip().lower()
    if content_type not in _ALLOWED_IMAGE_CONTENT_TYPES:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Unexpected content type from Jellyfin")
    return Response(
        content=image.content,
        media_type=content_type,
        headers={"Cache-Control": "private, max-age=86400", "X-Content-Type-Options": "nosniff"},
    )
