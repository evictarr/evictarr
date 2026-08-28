from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.settings import AppSettingsOut, AppSettingsUpdateRequest
from app.auth.dependencies import get_current_user
from app.core.scheduler import _EXECUTOR_JOB_ID, _SCAN_JOB_ID
from app.db.base import get_db
from app.db.models import AppSettings

router = APIRouter(prefix="/api/settings", tags=["settings"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=AppSettingsOut)
async def get_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AppSettings).where(AppSettings.id == 1))
    return result.scalar_one()


@router.put("", response_model=AppSettingsOut)
async def update_settings(payload: AppSettingsUpdateRequest, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AppSettings).where(AppSettings.id == 1))
    settings = result.scalar_one()
    for field, value in payload.model_dump().items():
        setattr(settings, field, value)
    await db.commit()
    await db.refresh(settings)

    scheduler = getattr(request.app.state, "scheduler", None)
    if scheduler is not None:
        scheduler.reschedule_job(
            _SCAN_JOB_ID, trigger=CronTrigger(hour=settings.scheduler_time.hour, minute=settings.scheduler_time.minute)
        )
        scheduler.reschedule_job(
            _EXECUTOR_JOB_ID, trigger=IntervalTrigger(minutes=settings.executor_interval_minutes)
        )

    return settings
