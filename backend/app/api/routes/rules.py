from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.rules import RuleCreateRequest, RuleOut, RuleUpdateRequest
from app.auth.dependencies import get_current_user
from app.db.base import get_db
from app.db.models import Rule

router = APIRouter(prefix="/api/rules", tags=["rules"], dependencies=[Depends(get_current_user)])


async def _get_rule_or_404(db: AsyncSession, rule_id: int) -> Rule:
    rule = await db.get(Rule, rule_id)
    if rule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rule not found")
    return rule


@router.get("", response_model=list[RuleOut])
async def list_rules(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Rule).order_by(Rule.id))
    return list(result.scalars().all())


@router.post("", response_model=RuleOut, status_code=status.HTTP_201_CREATED)
async def create_rule(payload: RuleCreateRequest, db: AsyncSession = Depends(get_db)):
    rule = Rule(**payload.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.get("/{rule_id}", response_model=RuleOut)
async def get_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    return await _get_rule_or_404(db, rule_id)


@router.put("/{rule_id}", response_model=RuleOut)
async def update_rule(rule_id: int, payload: RuleUpdateRequest, db: AsyncSession = Depends(get_db)):
    rule = await _get_rule_or_404(db, rule_id)
    for field, value in payload.model_dump().items():
        setattr(rule, field, value)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    rule = await _get_rule_or_404(db, rule_id)
    await db.delete(rule)
    await db.commit()


@router.post("/{rule_id}/toggle", response_model=RuleOut)
async def toggle_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    rule = await _get_rule_or_404(db, rule_id)
    rule.enabled = not rule.enabled
    await db.commit()
    await db.refresh(rule)
    return rule
