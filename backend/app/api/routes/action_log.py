from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.action_log import ActionLogOut, PendingDeletionSummary
from app.auth.dependencies import get_current_user
from app.db.base import get_db
from app.db.models import ActionLog, PendingDeletion

router = APIRouter(prefix="/api/action-log", tags=["action-log"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[ActionLogOut])
async def list_action_log(
    pending_deletion_id: int | None = Query(default=None),
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(ActionLog, PendingDeletion)
        .join(PendingDeletion, ActionLog.pending_deletion_id == PendingDeletion.id)
        .order_by(ActionLog.id.desc())
        .limit(limit)
        .offset(offset)
    )
    if pending_deletion_id is not None:
        query = query.where(ActionLog.pending_deletion_id == pending_deletion_id)

    result = await db.execute(query)
    out = []
    for action, pending in result.all():
        out.append(
            ActionLogOut(
                id=action.id,
                pending_deletion=PendingDeletionSummary(id=pending.id, title=pending.title, media_type=pending.media_type),
                seerr_status=action.seerr_status,
                radarr_sonarr_status=action.radarr_sonarr_status,
                disk_status=action.disk_status,
                overall_status=action.overall_status,
                error_detail=action.error_detail,
                executed_at=action.executed_at,
            )
        )
    return out
