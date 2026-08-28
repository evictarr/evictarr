from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.dashboard import WatchedStatusResponse
from app.auth.dependencies import get_current_user
from app.db.base import get_db
from app.rules.engine import preview_watched_status

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"], dependencies=[Depends(get_current_user)])


@router.get("/watched-status", response_model=WatchedStatusResponse)
async def watched_status(db: AsyncSession = Depends(get_db)):
    return await preview_watched_status(db)
