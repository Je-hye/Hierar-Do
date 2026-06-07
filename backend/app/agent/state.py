from datetime import date
from typing import Optional, TypedDict

from pydantic import BaseModel


class ParsedTodo(BaseModel):
    title: str
    estimated_minutes: int
    due_date: Optional[date] = None


class ParsedMilestone(BaseModel):
    title: str
    week_number: int
    todos: list[ParsedTodo]


class ParsedGoal(BaseModel):
    title: str
    deadline: date


class HierarDoState(TypedDict):
    user_id: int
    raw_input: str
    available_hours: dict  # {"weekday": int, "weekend": int}
    goal: Optional[ParsedGoal]
    milestones: list[ParsedMilestone]
    error: Optional[str]


# --- Smart Rescheduling State ---

class RescheduleTodoInfo(BaseModel):
    id: int
    title: str
    due_date: Optional[date] = None
    estimated_minutes: int
    actual_minutes: Optional[int] = None
    is_done: bool


class RescheduleMilestoneInfo(BaseModel):
    id: int
    title: str
    week_number: int
    todos: list[RescheduleTodoInfo] = []


class RescheduleState(TypedDict):
    goal_id: int
    goal_title: str
    deadline: date
    available_hours_weekday: int
    available_hours_weekend: int
    milestones: list[RescheduleMilestoneInfo]
    
    # analyze_progress output
    analysis: Optional[dict]
    
    # smart_reschedule output
    overall_summary: Optional[str]
    at_risk: Optional[bool]
    suggestions: Optional[list[dict]]  # [{"todo_id": int, "suggested_due_date": date, "reason": str}]
    
    error: Optional[str]
