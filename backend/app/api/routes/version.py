from fastapi import APIRouter, Depends

from app.api.schemas.version import VersionResponse
from app.auth.dependencies import get_current_user
from app.core.version import get_app_version

router = APIRouter(prefix="/api/version", tags=["version"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=VersionResponse)
async def version():
    return VersionResponse(version=get_app_version())
