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
