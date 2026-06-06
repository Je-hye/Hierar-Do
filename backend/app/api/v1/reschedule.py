from datetime import date, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.goal import Goal, GoalStatus
from app.models.milestone import Milestone
from app.models.todo import Todo

router = APIRouter(prefix="/reschedule", tags=["reschedule"])


class RescheduleItem(BaseModel):
    todo_id: int
    title: str
    old_due_date: date | None
    new_due_date: date


def _day_capacity_minutes(d: date, weekday_hours: int, weekend_hours: int) -> int:
    """해당 날짜의 가용 시간(분) 반환. 토/일 = weekend, 나머지 = weekday."""
    # weekday(): 0=월 ~ 6=일
    if d.weekday() >= 5:
        return weekend_hours * 60
    return weekday_hours * 60


def _compute_reschedule(goals: list[Goal]) -> list[tuple[Todo, date]]:
    """각 Goal의 가용 시간을 고려해 미완료 Todo를 오늘~deadline 사이에 재배치.

    알고리즘:
    - 날짜를 오늘부터 deadline까지 순회하며 '하루 용량(분)' 버킷을 채운다.
    - Todo를 순서대로 배치하되, 남은 용량이 부족하면 다음 날로 이월한다.
    - available_hours가 없는 Goal은 기존 균등 분배 방식을 사용한다.
    """
    today = date.today()
    result: list[tuple[Todo, date]] = []

    for goal in goals:
        todos = [t for m in goal.milestones for t in m.todos if not t.is_done]
        if not todos:
            continue

        wkd = goal.available_hours_weekday
        wke = goal.available_hours_weekend

        # available_hours가 없으면 기존 균등 분배
        if not wkd or not wke:
            remaining = max((goal.deadline - today).days, 0)
            n = len(todos)
            for i, todo in enumerate(todos):
                if remaining == 0 or n == 1:
                    new_date = today
                else:
                    offset = int(i * remaining / (n - 1))
                    new_date = min(today + timedelta(days=offset), goal.deadline)
                result.append((todo, new_date))
            continue

        # 날짜 버킷 기반 배치
        current_day = today
        remaining_today = _day_capacity_minutes(current_day, wkd, wke)

        for todo in todos:
            needed = todo.estimated_minutes or 30
            # 남은 용량이 없으면 다음 날로 이동
            while remaining_today <= 0 and current_day < goal.deadline:
                current_day += timedelta(days=1)
                remaining_today = _day_capacity_minutes(current_day, wkd, wke)

            result.append((todo, min(current_day, goal.deadline)))
            remaining_today -= needed

    return result


async def _load_goals(current_user: User, db: AsyncSession) -> list[Goal]:
    rows = await db.execute(
        select(Goal)
        .where(Goal.user_id == current_user.id, Goal.status != GoalStatus.done)
        .options(selectinload(Goal.milestones).selectinload(Milestone.todos))
    )
    return list(rows.scalars().all())


@router.post("/preview", response_model=list[RescheduleItem])
async def preview_reschedule(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    goals = await _load_goals(current_user, db)
    changes = _compute_reschedule(goals)
    return [
        RescheduleItem(
            todo_id=todo.id,
            title=todo.title,
            old_due_date=todo.due_date,
            new_due_date=new_date,
        )
        for todo, new_date in changes
        if todo.due_date != new_date
    ]


@router.post("/apply", response_model=dict)
async def apply_reschedule(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    goals = await _load_goals(current_user, db)
    changes = _compute_reschedule(goals)
    count = 0
    for todo, new_date in changes:
        if todo.due_date != new_date:
            todo.due_date = new_date
            count += 1
    if count:
        await db.commit()
    return {"updated": count}
