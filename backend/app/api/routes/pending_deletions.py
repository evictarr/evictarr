from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.pending_deletions import CancelRequest, PendingDeletionOut
from app.auth.dependencies import get_current_user
from app.db.base import get_db
from app.db.models import PendingDeletion, PendingStatus
from app.deletions import queue_service

router = APIRouter(prefix="/api/pending-deletions", tags=["pending-deletions"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[PendingDeletionOut])
async def list_pending_deletions(
    status_filter: PendingStatus | None = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
):
    query = select(PendingDeletion).order_by(PendingDeletion.execute_after)
    if status_filter is not None:
        query = query.where(PendingDeletion.status == status_filter)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{pending_id}", response_model=PendingDeletionOut)
async def get_pending_deletion(pending_id: int, db: AsyncSession = Depends(get_db)):
    pending = await db.get(PendingDeletion, pending_id)
    if pending is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    return pending


@router.post("/{pending_id}/cancel", response_model=PendingDeletionOut)
async def cancel_pending_deletion(pending_id: int, payload: CancelRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await queue_service.cancel(db, pending_id, payload.reason)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
