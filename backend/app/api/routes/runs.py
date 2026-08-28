from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.runs import RunEventOut, RunNowRequest, RunOut
from app.auth.dependencies import get_current_user
from app.db.base import get_db
from app.db.models import Run, RunEvent, RunType, User
from app.rules.engine import run_scan

router = APIRouter(prefix="/api/runs", tags=["runs"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[RunOut])
async def list_runs(limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Run).order_by(Run.id.desc()).limit(limit).offset(offset))
    return list(result.scalars().all())


@router.get("/{run_id}", response_model=RunOut)
async def get_run(run_id: int, db: AsyncSession = Depends(get_db)):
    run = await db.get(Run, run_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")
    return run


@router.get("/{run_id}/events", response_model=list[RunEventOut])
async def get_run_events(run_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RunEvent).where(RunEvent.run_id == run_id).order_by(RunEvent.id))
    return list(result.scalars().all())


@router.post("/run-now", response_model=RunOut)
async def run_now(payload: RunNowRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    run = await run_scan(db, RunType.manual, f"user:{user.username}", payload.rule_ids)
    return run
