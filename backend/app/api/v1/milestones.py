"""Milestone CRUD endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.milestone import Milestone
from app.models.todo import Todo
from app.models.goal import Goal
from app.models.user import User
from app.schemas.goal import MilestoneOut, UpdateMilestoneRequest
from app.api.dependencies import get_current_user

router = APIRouter(prefix="/milestones", tags=["milestones"])


async def _get_milestone_or_404(milestone_id: int, current_user: User, db: AsyncSession) -> Milestone:
    rows = await db.execute(
        select(Milestone)
        .join(Goal, Milestone.goal_id == Goal.id)
        .where(Milestone.id == milestone_id, Goal.user_id == current_user.id)
        .options(selectinload(Milestone.todos))
    )
    ms = rows.scalar_one_or_none()
    if not ms:
        raise HTTPException(status_code=404, detail="Milestone not found")
    return ms


# ── Update ───────────────────────────────────────────────────────────────────

@router.patch("/{milestone_id}", response_model=MilestoneOut)
async def update_milestone(
    milestone_id: int, req: UpdateMilestoneRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    ms = await _get_milestone_or_404(milestone_id, current_user, db)
    if req.title is not None:
        ms.title = req.title
    await db.commit()
    await db.refresh(ms)
    # todos 관계가 lazy load될 수 있어 다시 로드
    rows = await db.execute(
        select(Milestone)
        .where(Milestone.id == milestone_id)
        .options(selectinload(Milestone.todos))
    )
    ms = rows.scalar_one()
    return MilestoneOut.model_validate(ms)
