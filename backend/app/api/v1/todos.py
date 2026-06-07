"""Todo CRUD endpoints.

mark_done / mark_undone 시 부모 Milestone 및 Goal의 status를 자동으로 업데이트합니다.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.goal import Goal, GoalStatus
from app.models.milestone import Milestone, MilestoneStatus
from app.models.todo import Todo
from app.models.user import User
from app.schemas.goal import CreateTodoRequest, TodoOut, UpdateTodoRequest
from app.api.dependencies import get_current_user

router = APIRouter(prefix="/todos", tags=["todos"])


async def _get_todo_or_404(todo_id: int, current_user: User, db: AsyncSession) -> Todo:
    # Todo -> Milestone -> Goal의 user_id 확인
    result = await db.execute(
        select(Todo)
        .join(Milestone, Todo.milestone_id == Milestone.id)
        .join(Goal, Milestone.goal_id == Goal.id)
        .where(Todo.id == todo_id, Goal.user_id == current_user.id)
    )
    todo = result.scalar_one_or_none()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo


async def _sync_parent_status(todo: Todo, db: AsyncSession) -> None:
    """Todo 변경 후 부모 Milestone → Goal 완료 상태를 자동 동기화."""
    rows = await db.execute(
        select(Goal)
        .where(Goal.id == (
            select(Milestone.goal_id)
            .where(Milestone.id == todo.milestone_id)
            .scalar_subquery()
        ))
        .options(selectinload(Goal.milestones).selectinload(Milestone.todos))
    )
    goal = rows.scalar_one_or_none()
    if not goal:
        return

    for ms in goal.milestones:
        if ms.todos:
            ms_done = all(t.is_done for t in ms.todos)
            ms.status = MilestoneStatus.done if ms_done else MilestoneStatus.active

    all_done = all(t.is_done for ms in goal.milestones for t in ms.todos)
    goal.status = GoalStatus.done if all_done else GoalStatus.active


# ── Toggle ──────────────────────────────────────────────────────────────────

@router.patch("/{todo_id}/done", response_model=TodoOut)
async def mark_done(todo_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    todo = await _get_todo_or_404(todo_id, current_user, db)
    todo.is_done = True
    await db.flush()
    await _sync_parent_status(todo, db)
    await db.commit()
    await db.refresh(todo)
    return TodoOut.model_validate(todo)


@router.patch("/{todo_id}/undone", response_model=TodoOut)
async def mark_undone(todo_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    todo = await _get_todo_or_404(todo_id, current_user, db)
    todo.is_done = False
    await db.flush()
    await _sync_parent_status(todo, db)
    await db.commit()
    await db.refresh(todo)
    return TodoOut.model_validate(todo)


# ── Create ───────────────────────────────────────────────────────────────────

@router.post("", response_model=TodoOut, status_code=201)
async def create_todo(req: CreateTodoRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    # milestone 존재 및 소유권 확인
    rows = await db.execute(
        select(Milestone)
        .join(Goal, Milestone.goal_id == Goal.id)
        .where(Milestone.id == req.milestone_id, Goal.user_id == current_user.id)
    )
    ms = rows.scalar_one_or_none()
    if not ms:
        raise HTTPException(status_code=404, detail="Milestone not found")
    todo = Todo(
        milestone_id=req.milestone_id,
        title=req.title,
        due_date=req.due_date,
        estimated_minutes=req.estimated_minutes,
        suggested_by_ai=False,
    )
    db.add(todo)
    await db.commit()
    await db.refresh(todo)
    return TodoOut.model_validate(todo)


# ── Update ───────────────────────────────────────────────────────────────────

@router.patch("/{todo_id}", response_model=TodoOut)
async def update_todo(todo_id: int, req: UpdateTodoRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    todo = await _get_todo_or_404(todo_id, current_user, db)
    if req.title is not None:
        todo.title = req.title
    if req.due_date is not None:
        todo.due_date = req.due_date
    if req.estimated_minutes is not None:
        todo.estimated_minutes = req.estimated_minutes
    await db.commit()
    await db.refresh(todo)
    return TodoOut.model_validate(todo)


# ── Delete ───────────────────────────────────────────────────────────────────

@router.delete("/{todo_id}", status_code=204)
async def delete_todo(todo_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    todo = await _get_todo_or_404(todo_id, current_user, db)
    await db.delete(todo)
    await db.commit()
