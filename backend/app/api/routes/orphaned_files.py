from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.orphaned_files import OrphanedFileOut, OrphanedScanResponse
from app.auth.dependencies import get_current_user
from app.db.base import get_db
from app.db.models import OrphanedFile, OrphanedStatus
from app.orphaned.scanner import run_scan

router = APIRouter(prefix="/api/orphaned-files", tags=["orphaned-files"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[OrphanedFileOut])
async def list_orphaned_files(
    status_filter: OrphanedStatus | None = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
):
    query = select(OrphanedFile).order_by(OrphanedFile.detected_at.desc())
    if status_filter is not None:
        query = query.where(OrphanedFile.status == status_filter)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("/scan", response_model=OrphanedScanResponse)
async def scan_now(db: AsyncSession = Depends(get_db)):
    found = await run_scan(db)
    return OrphanedScanResponse(found=found)


@router.post("/{orphaned_id}/clear", response_model=OrphanedFileOut)
async def clear_orphaned_file(orphaned_id: int, db: AsyncSession = Depends(get_db)):
    row = await db.get(OrphanedFile, orphaned_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    row.status = OrphanedStatus.cleared
    row.cleared_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(row)
    return row
