from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class GoalStatus(str, Enum):
    pending = "pending"
    active = "active"
    done = "done"


class TodoOut(BaseModel):
    id: int
    milestone_id: int
    title: str
    due_date: Optional[date]
    estimated_minutes: int
    is_done: bool
    suggested_by_ai: bool

    model_config = {"from_attributes": True}


class MilestoneOut(BaseModel):
    id: int
    goal_id: int
    title: str
    week_number: int
    status: str
    suggested_by_ai: bool
    todos: list[TodoOut] = []

    model_config = {"from_attributes": True}


class GoalOut(BaseModel):
    id: int
    title: str
    raw_input: str
    deadline: date
    status: GoalStatus
    created_at: datetime
    available_hours_weekday: Optional[int] = None
    available_hours_weekend: Optional[int] = None
    milestones: list[MilestoneOut] = []

    model_config = {"from_attributes": True}


class AvailableHours(BaseModel):
    weekday: int = Field(ge=1, le=24, description="평일 하루 가용 시간 (1~24)")
    weekend: int = Field(ge=1, le=24, description="주말 하루 가용 시간 (1~24)")


class CreateGoalRequest(BaseModel):
    raw_input: str = Field(min_length=5, max_length=500, description="자연어 목표 입력")
    available_hours: AvailableHours


class CreateGoalResponse(BaseModel):
    goal: GoalOut
    milestones: list[MilestoneOut]
    todos: list[TodoOut]


# ── 편집/생성 요청 스키마 ───────────────────────────────────────────────────

class UpdateTodoRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=500)
    due_date: Optional[date] = None
    estimated_minutes: Optional[int] = Field(default=None, ge=1, le=1440)


class CreateTodoRequest(BaseModel):
    milestone_id: int
    title: str = Field(min_length=1, max_length=500)
    due_date: Optional[date] = None
    estimated_minutes: int = Field(default=30, ge=1, le=1440)


class UpdateMilestoneRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=500)


class UpdateGoalStatusRequest(BaseModel):
    status: GoalStatus


# ── AI 재조정 제안 스키마 ──────────────────────────────────────────────────

class TodoSuggestion(BaseModel):
    todo_id: int
    title: str
    current_due_date: Optional[date]
    suggested_due_date: date
    reason: str


class SuggestionResponse(BaseModel):
    goal_id: int
    overall_summary: str
    at_risk: bool
    suggestions: list[TodoSuggestion]


class ApplySuggestionItem(BaseModel):
    todo_id: int
    new_due_date: date


class ApplySuggestionRequest(BaseModel):
    items: list[ApplySuggestionItem]
