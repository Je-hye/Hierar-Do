import json
import re
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agent.client import client
from app.agent.graph import pipeline
from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.goal import Goal, GoalStatus
from app.models.milestone import Milestone
from app.models.todo import Todo
from app.schemas.goal import (
    ApplySuggestionRequest,
    CreateGoalRequest,
    CreateGoalResponse,
    GoalOut,
    MilestoneOut,
    SuggestionResponse,
    TodoOut,
    TodoSuggestion,
    UpdateGoalStatusRequest,
)

router = APIRouter(prefix="/goals", tags=["goals"])


@router.post("", response_model=CreateGoalResponse)
async def create_goal(
    req: CreateGoalRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    state = {
        "raw_input": req.raw_input,
        # AvailableHours Pydantic 모델 → dict로 변환하여 state에 전달
        "available_hours": req.available_hours.model_dump(),
        "goal": None,
        "milestones": [],
        "error": None,
    }
    result = await pipeline.ainvoke(state)

    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])

    parsed_goal = result["goal"]
    parsed_milestones = result["milestones"]

    goal = Goal(
        user_id=current_user.id,
        title=parsed_goal.title,
        raw_input=req.raw_input,
        deadline=parsed_goal.deadline,
        available_hours_weekday=req.available_hours.weekday,
        available_hours_weekend=req.available_hours.weekend,
    )
    db.add(goal)
    await db.flush()

    for pm in parsed_milestones:
        milestone = Milestone(
            goal_id=goal.id,
            title=pm.title,
            week_number=pm.week_number,
            suggested_by_ai=True,
        )
        db.add(milestone)
        await db.flush()
        for pt in pm.todos:
            db.add(
                Todo(
                    milestone_id=milestone.id,
                    title=pt.title,
                    due_date=pt.due_date,
                    estimated_minutes=pt.estimated_minutes,
                    suggested_by_ai=True,
                )
            )

    await db.commit()

    rows = await db.execute(
        select(Goal)
        .options(selectinload(Goal.milestones).selectinload(Milestone.todos))
        .where(Goal.id == goal.id)
    )
    goal = rows.scalar_one()

    all_todos = [t for m in goal.milestones for t in m.todos]
    return CreateGoalResponse(
        goal=GoalOut.model_validate(goal),
        milestones=[MilestoneOut.model_validate(m) for m in goal.milestones],
        todos=[TodoOut.model_validate(t) for t in all_todos],
    )


@router.get("", response_model=list[GoalOut])
async def list_goals(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = await db.execute(
        select(Goal)
        .where(Goal.user_id == current_user.id)
        .options(selectinload(Goal.milestones).selectinload(Milestone.todos))
        .order_by(Goal.created_at.desc())
    )
    return [GoalOut.model_validate(g) for g in rows.scalars().all()]


@router.get("/{goal_id}", response_model=GoalOut)
async def get_goal(goal_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = await db.execute(
        select(Goal)
        .where(Goal.id == goal_id, Goal.user_id == current_user.id)
        .options(selectinload(Goal.milestones).selectinload(Milestone.todos))
    )
    goal = rows.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return GoalOut.model_validate(goal)


@router.delete("/{goal_id}", status_code=204)
async def delete_goal(goal_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = await db.execute(
        select(Goal).where(Goal.id == goal_id, Goal.user_id == current_user.id)
    )
    goal = rows.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    await db.delete(goal)
    await db.commit()


@router.patch("/{goal_id}/status", response_model=GoalOut)
async def update_goal_status(
    goal_id: int, req: UpdateGoalStatusRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    rows = await db.execute(
        select(Goal)
        .where(Goal.id == goal_id, Goal.user_id == current_user.id)
        .options(selectinload(Goal.milestones).selectinload(Milestone.todos))
    )
    goal = rows.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    goal.status = req.status
    await db.commit()
    await db.refresh(goal)
    rows = await db.execute(
        select(Goal)
        .where(Goal.id == goal_id)
        .options(selectinload(Goal.milestones).selectinload(Milestone.todos))
    )
    goal = rows.scalar_one()
    return GoalOut.model_validate(goal)


@router.get("/{goal_id}/suggest", response_model=SuggestionResponse)
async def suggest_goal(goal_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Claude API를 통해 목표 진첩률을 분석하고 할 일 재조정 제안을 생성합니다."""
    rows = await db.execute(
        select(Goal)
        .where(Goal.id == goal_id, Goal.user_id == current_user.id)
        .options(selectinload(Goal.milestones).selectinload(Milestone.todos))
    )
    goal = rows.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    if goal.status == GoalStatus.done:
        raise HTTPException(status_code=400, detail="이미 완료된 목표는 재조정 제안이 필요하지 않습니다.")

    # ─ 진첩 분석 ─────────────────────────────────────────────────────────────
    today = date.today()
    all_todos = [t for m in goal.milestones for t in m.todos]
    done_todos = [t for t in all_todos if t.is_done]
    pending_todos = [t for t in all_todos if not t.is_done]
    overdue_todos = [t for t in pending_todos if t.due_date and t.due_date < today]
    upcoming_todos = [t for t in pending_todos if t not in overdue_todos]
    days_remaining = max((goal.deadline - today).days, 0)
    pct = round(len(done_todos) / len(all_todos) * 100) if all_todos else 0

    overdue_lines = "\n".join(
        f"- [id:{t.id}] {t.title} (원래 날짜: {t.due_date}, 예상 {t.estimated_minutes}분)"
        for t in overdue_todos
    ) or "없음"
    upcoming_lines = "\n".join(
        f"- [id:{t.id}] {t.title} (예정: {t.due_date}, 예상 {t.estimated_minutes}분)"
        for t in upcoming_todos
    ) or "없음"

    # ─ Claude API 호출 ──────────────────────────────────────────────────────────
    system = """당신은 목표 관리 에이전트입니다. 사용자의 목표 진첩률을 분석하고 구체적인 재조정 제안을 한국어로 제공하세요.
JSON만 반환하세요 (설명 텍스트 금지):
{
  "overall_summary": "1~2문장 한국어 평가",
  "at_risk": true or false,
  "suggestions": [
    {
      "todo_id": number,
      "title": "string",
      "current_due_date": "YYYY-MM-DD or null",
      "suggested_due_date": "YYYY-MM-DD",
      "reason": "한국어 이유"
    }
  ]
}
재조정이 필요한 할 일만 suggestions에 포함하세요. 완료된 할 일은 제외하세요."""
    user_msg = (
        f"목표: {goal.title}\n"
        f"마감일: {goal.deadline} (D-{days_remaining})\n"
        f"진행률: {pct}% ({len(done_todos)}/{len(all_todos)} 완료)\n"
        f"오늘: {today}\n\n"
        f"기한 초과 할 일:\n{overdue_lines}\n\n"
        f"예정된 할 일:\n{upcoming_lines}"
    )
    try:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise HTTPException(status_code=500, detail="AI 응답 파싱 실패")
        data = json.loads(match.group())
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"AI 응답 파싱 실패: {e}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 분석 실패: {e}")

    # ─ 응답 조립 ──────────────────────────────────────────────────────────────
    todo_map = {t.id: t for t in all_todos}
    suggestions = []
    for s in data.get("suggestions", []):
        todo = todo_map.get(s.get("todo_id"))
        if not todo:
            continue
        try:
            suggested = date.fromisoformat(s["suggested_due_date"])
        except (KeyError, ValueError):
            continue
        # 마감일 키원프
        suggested = min(suggested, goal.deadline)
        suggestions.append(
            TodoSuggestion(
                todo_id=todo.id,
                title=todo.title,
                current_due_date=todo.due_date,
                suggested_due_date=suggested,
                reason=s.get("reason", ""),
            )
        )
    return SuggestionResponse(
        goal_id=goal.id,
        overall_summary=data.get("overall_summary", ""),
        at_risk=bool(data.get("at_risk", False)),
        suggestions=suggestions,
    )


@router.post("/{goal_id}/apply", response_model=dict)
async def apply_suggestion(
    goal_id: int, req: ApplySuggestionRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """AI 제안을 승인하여 DB에 적용합니다."""
    rows = await db.execute(
        select(Goal).where(Goal.id == goal_id, Goal.user_id == current_user.id)
    )
    if not rows.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Goal not found")

    count = 0
    for item in req.items:
        result = await db.execute(select(Todo).where(Todo.id == item.todo_id))
        todo = result.scalar_one_or_none()
        if todo and not todo.is_done:
            todo.due_date = item.new_due_date
            count += 1
    if count:
        await db.commit()
    return {"updated": count}
