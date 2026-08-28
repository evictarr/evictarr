import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from app.db.base import async_session_factory
from app.db.models import AppSettings, RunType
from app.deletions.executor import execute_due
from app.orphaned.scanner import run_scan as run_orphaned_scan
from app.rules.engine import run_scan

logger = logging.getLogger(__name__)

_SCAN_JOB_ID = "daily_scan"
_EXECUTOR_JOB_ID = "grace_period_executor"


async def _run_scheduled_scan() -> None:
    async with async_session_factory() as db:
        try:
            run = await run_scan(db, RunType.scheduled, "scheduler")
            logger.info(
                "Scheduled scan finished: scanned=%s matched=%s skipped=%s",
                run.items_scanned,
                run.items_matched,
                run.items_skipped,
            )
        except Exception:
            logger.exception("Scheduled scan failed")

        try:
            found = await run_orphaned_scan(db)
            if found:
                logger.info("Orphaned-file scan found %s new file(s)", found)
        except Exception:
            logger.exception("Orphaned-file scan failed")


async def _run_executor() -> None:
    async with async_session_factory() as db:
        try:
            executed = await execute_due(db)
            if executed:
                logger.info("Grace-period executor processed %s item(s)", len(executed))
        except Exception:
            logger.exception("Grace-period executor failed")


async def _load_settings(db) -> AppSettings:
    result = await db.execute(select(AppSettings).where(AppSettings.id == 1))
    settings = result.scalar_one_or_none()
    return settings


async def start_scheduler() -> AsyncIOScheduler:
    async with async_session_factory() as db:
        settings = await _load_settings(db)

    hour, minute = (3, 30)
    executor_interval_minutes = 15
    if settings is not None:
        hour, minute = settings.scheduler_time.hour, settings.scheduler_time.minute
        executor_interval_minutes = settings.executor_interval_minutes

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _run_scheduled_scan,
        CronTrigger(hour=hour, minute=minute),
        id=_SCAN_JOB_ID,
        replace_existing=True,
    )
    scheduler.add_job(
        _run_executor,
        IntervalTrigger(minutes=executor_interval_minutes),
        id=_EXECUTOR_JOB_ID,
        replace_existing=True,
    )
    scheduler.start()
    return scheduler
