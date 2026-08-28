from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    ActionLog,
    OverallStatus,
    PendingDeletion,
    PendingMediaType,
    PendingStatus,
    ServiceName,
    SystemStatus,
)
from app.integrations import service as integration_service
from app.integrations.base_client import IntegrationError
from app.notifications.dispatcher import notify_executed


async def _delete_from_seerr(db: AsyncSession, external_ids: dict) -> SystemStatus:
    request_id = external_ids.get("seerr_request_id")
    if not request_id:
        return SystemStatus.skipped
    integration = await integration_service.get_integration(db, ServiceName.seerr)
    if integration is None or not integration.enabled:
        return SystemStatus.skipped
    try:
        client = integration_service.build_client(integration)
        await client.delete_request(request_id)
        return SystemStatus.success
    except IntegrationError:
        return SystemStatus.failed


async def _delete_from_arr(db: AsyncSession, media_type: PendingMediaType, external_ids: dict) -> SystemStatus:
    try:
        if media_type == PendingMediaType.movie:
            integration = await integration_service.get_integration(db, ServiceName.radarr)
            if integration is None or not integration.enabled:
                return SystemStatus.skipped
            client = integration_service.build_client(integration)
            await client.delete_movie(external_ids["radarr_movie_id"], delete_files=True)
        elif media_type == PendingMediaType.series:
            integration = await integration_service.get_integration(db, ServiceName.sonarr)
            if integration is None or not integration.enabled:
                return SystemStatus.skipped
            client = integration_service.build_client(integration)
            await client.delete_series(external_ids["sonarr_series_id"], delete_files=True)
        elif media_type == PendingMediaType.season:
            integration = await integration_service.get_integration(db, ServiceName.sonarr)
            if integration is None or not integration.enabled:
                return SystemStatus.skipped
            client = integration_service.build_client(integration)
            series_id = external_ids["sonarr_series_id"]
            season_number = external_ids["season_number"]
            await client.unmonitor_season(series_id, season_number)
            await client.delete_season_files(series_id, season_number)
        return SystemStatus.success
    except IntegrationError:
        return SystemStatus.failed


def _overall_status(seerr: SystemStatus, arr: SystemStatus) -> OverallStatus:
    relevant = [s for s in (seerr, arr) if s != SystemStatus.skipped]
    if not relevant or all(s == SystemStatus.success for s in relevant):
        return OverallStatus.success
    if any(s == SystemStatus.success for s in relevant):
        return OverallStatus.partial_failure
    return OverallStatus.failed


async def _execute_one(db: AsyncSession, pending: PendingDeletion) -> None:
    pending.status = PendingStatus.executing
    await db.commit()

    seerr_status = await _delete_from_seerr(db, pending.external_ids)
    arr_status = await _delete_from_arr(db, pending.media_type, pending.external_ids)
    overall = _overall_status(seerr_status, arr_status)

    action = ActionLog(
        pending_deletion_id=pending.id,
        seerr_status=seerr_status,
        radarr_sonarr_status=arr_status,
        # Evictarr never issues a raw filesystem delete - disk removal is
        # always a side effect of the *arr deleteFiles flag, so this
        # mirrors the arr call's own outcome rather than an independent check.
        disk_status=arr_status,
        overall_status=overall,
        error_detail=None if overall == OverallStatus.success else {"seerr": seerr_status.value, "radarr_sonarr": arr_status.value},
    )
    db.add(action)
    pending.status = PendingStatus.failed if overall == OverallStatus.failed else PendingStatus.completed
    await db.commit()
    await db.refresh(action)
    await notify_executed(db, pending, action)


async def execute_due(db: AsyncSession) -> list[PendingDeletion]:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(PendingDeletion).where(PendingDeletion.status == PendingStatus.pending, PendingDeletion.execute_after <= now)
    )
    due = list(result.scalars().all())
    for pending in due:
        await _execute_one(db, pending)
    return due
