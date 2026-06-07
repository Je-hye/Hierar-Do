# Backend Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** FastAPI 백엔드를 구축하고 LangGraph 파이프라인으로 목표를 분해하는 API를 구현한다.

**Architecture:** 선형 LangGraph 파이프라인(parse_goal → decompose → schedule)이 Claude API를 호출해 목표를 마일스톤/할 일로 분해한다. FastAPI가 비동기 SQLAlchemy + asyncpg로 PostgreSQL에 결과를 저장한다. MVP는 인증 없이 user_id=1 고정.

**Tech Stack:** FastAPI, LangGraph, Anthropic SDK (claude-sonnet-4-6), SQLAlchemy 2.0 async, asyncpg, PostgreSQL, Poetry

---

## File Structure

```
backend/
├── app/
│   ├── main.py                          # FastAPI app, CORS, 라우터
│   ├── api/v1/
│   │   ├── __init__.py
│   │   ├── goals.py                     # Goals 엔드포인트
│   │   └── todos.py                     # Todos 엔드포인트
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── graph.py                     # LangGraph 파이프라인 조립
│   │   ├── state.py                     # HierarDoState + Parsed* Pydantic 모델
│   │   └── nodes/
│   │       ├── __init__.py
│   │       ├── parse_goal.py            # Claude API: NL → ParsedGoal
│   │       ├── decompose.py             # Claude API: Goal → 4 Milestones + Todos
│   │       └── schedule.py              # Pure Python: Todo에 due_date 배분
│   ├── models/
│   │   ├── __init__.py                  # 모든 모델 re-export (create_all용)
│   │   ├── user.py
│   │   ├── goal.py
│   │   ├── milestone.py
│   │   └── todo.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── goal.py                      # Pydantic 요청/응답 스키마
│   └── db/
│       ├── __init__.py
│       ├── session.py                   # engine, AsyncSessionLocal, Base, get_db
│       └── init_db.py                   # create_all 헬퍼
├── tests/
│   ├── __init__.py
│   ├── conftest.py                      # SQLite in-memory, TestClient
│   ├── test_schedule_node.py            # schedule 노드 단위 테스트
│   ├── test_goals_api.py                # Goals API 통합 테스트 (pipeline mock)
│   └── test_todos_api.py                # Todos API 통합 테스트
├── pyproject.toml
├── requirements.txt                     # poetry export 결과
├── .env.example
└── Dockerfile
```

---

## Task 1: Poetry 프로젝트 세팅

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/.env.example`
- Create: `backend/Dockerfile`

- [ ] **Step 1: backend 디렉토리 생성 후 pyproject.toml 작성**

```toml
[tool.poetry]
name = "hierar-do-backend"
version = "0.1.0"
description = "Hierar-Do Backend API"
authors = ["EunHye-03"]

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.115.0"
uvicorn = {extras = ["standard"], version = "^0.32.0"}
sqlalchemy = {extras = ["asyncio"], version = "^2.0.0"}
asyncpg = "^0.30.0"
langgraph = "^0.2.0"
anthropic = "^0.40.0"
pydantic = "^2.9.0"
pydantic-settings = "^2.6.0"
python-dotenv = "^1.0.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.3.0"
pytest-asyncio = "^0.24.0"
httpx = "^0.28.0"
aiosqlite = "^0.20.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 2: .env.example 작성**

```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
DATABASE_URL=postgresql+asyncpg://hierardo:hierardo@localhost:5432/hierardo
```

- [ ] **Step 3: Dockerfile 작성**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN pip install poetry==1.8.4

COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 4: 의존성 설치 및 requirements.txt 생성**

```bash
cd backend
poetry install
poetry export -f requirements.txt --output requirements.txt --without-hashes
```

Expected: `backend/requirements.txt` 파일 생성됨

- [ ] **Step 5: 커밋**

```bash
git add backend/pyproject.toml backend/.env.example backend/Dockerfile backend/requirements.txt
git commit -m "chore: Poetry 프로젝트 및 Docker 환경 설정"
```

---

## Task 2: DB 세션 및 Base 설정

**Files:**
- Create: `backend/app/__init__.py` (빈 파일)
- Create: `backend/app/db/__init__.py` (빈 파일)
- Create: `backend/app/db/session.py`
- Create: `backend/app/db/init_db.py`

- [ ] **Step 1: `backend/app/db/session.py` 작성**

```python
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

_raw_url = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://hierardo:hierardo@localhost:5432/hierardo",
)
DATABASE_URL = _raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

- [ ] **Step 2: `backend/app/db/init_db.py` 작성**

```python
from app.db.session import engine, Base
import app.models  # noqa: F401 — 모든 모델 등록 트리거


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

- [ ] **Step 3: 빈 `__init__.py` 파일 생성**

```bash
touch backend/app/__init__.py
touch backend/app/db/__init__.py
```

- [ ] **Step 4: 커밋**

```bash
git add backend/app/
git commit -m "feat: SQLAlchemy async 엔진 및 세션 설정"
```

---

## Task 3: SQLAlchemy 모델 정의

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/goal.py`
- Create: `backend/app/models/milestone.py`
- Create: `backend/app/models/todo.py`

- [ ] **Step 1: `backend/app/models/user.py` 작성**

```python
from sqlalchemy import Integer, String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    available_hours: Mapped[dict] = mapped_column(
        JSON, nullable=False, default={"weekday": 2, "weekend": 4}
    )

    goals = relationship("Goal", back_populates="user")
```

- [ ] **Step 2: `backend/app/models/goal.py` 작성**

```python
import enum
from datetime import date, datetime

from sqlalchemy import Integer, String, Date, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base


class GoalStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    done = "done"


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    raw_input: Mapped[str] = mapped_column(Text, nullable=False)
    deadline: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[GoalStatus] = mapped_column(
        Enum(GoalStatus, native_enum=False), nullable=False, default=GoalStatus.active
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user = relationship("User", back_populates="goals")
    milestones = relationship(
        "Milestone", back_populates="goal", cascade="all, delete-orphan"
    )
```

- [ ] **Step 3: `backend/app/models/milestone.py` 작성**

```python
import enum

from sqlalchemy import Integer, String, Enum, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class MilestoneStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    done = "done"


class Milestone(Base):
    __tablename__ = "milestones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    goal_id: Mapped[int] = mapped_column(Integer, ForeignKey("goals.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[MilestoneStatus] = mapped_column(
        Enum(MilestoneStatus, native_enum=False), nullable=False, default=MilestoneStatus.pending
    )
    suggested_by_ai: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    goal = relationship("Goal", back_populates="milestones")
    todos = relationship(
        "Todo", back_populates="milestone", cascade="all, delete-orphan"
    )
```

- [ ] **Step 4: `backend/app/models/todo.py` 작성**

```python
from datetime import date
from typing import Optional

from sqlalchemy import Integer, String, Date, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Todo(Base):
    __tablename__ = "todos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    milestone_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("milestones.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    is_done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    suggested_by_ai: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    milestone = relationship("Milestone", back_populates="todos")
```

- [ ] **Step 5: `backend/app/models/__init__.py` 작성 (모델 등록)**

```python
from app.models.user import User
from app.models.goal import Goal
from app.models.milestone import Milestone
from app.models.todo import Todo

__all__ = ["User", "Goal", "Milestone", "Todo"]
```

- [ ] **Step 6: 커밋**

```bash
git add backend/app/models/
git commit -m "feat: SQLAlchemy ORM 모델 정의 (User, Goal, Milestone, Todo)"
```

---

## Task 4: Pydantic 스키마 정의

**Files:**
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/goal.py`

- [ ] **Step 1: `backend/app/schemas/goal.py` 작성**

```python
from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


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
    milestones: list[MilestoneOut] = []

    model_config = {"from_attributes": True}


class CreateGoalRequest(BaseModel):
    raw_input: str
    available_hours: dict  # {"weekday": int, "weekend": int}


class CreateGoalResponse(BaseModel):
    goal: GoalOut
    milestones: list[MilestoneOut]
    todos: list[TodoOut]
```

- [ ] **Step 2: 빈 `__init__.py` 생성**

```bash
touch backend/app/schemas/__init__.py
```

- [ ] **Step 3: 커밋**

```bash
git add backend/app/schemas/
git commit -m "feat: Pydantic 요청/응답 스키마 정의"
```

---

## Task 5: LangGraph 상태 및 schedule 노드 (TDD)

**Files:**
- Create: `backend/app/agent/__init__.py`
- Create: `backend/app/agent/state.py`
- Create: `backend/app/agent/nodes/__init__.py`
- Create: `backend/app/agent/nodes/schedule.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/test_schedule_node.py`

- [ ] **Step 1: `backend/app/agent/state.py` 작성**

```python
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
    raw_input: str
    available_hours: dict  # {"weekday": int, "weekend": int}
    goal: Optional[ParsedGoal]
    milestones: list[ParsedMilestone]
    error: Optional[str]
```

- [ ] **Step 2: 실패할 schedule 테스트 작성 (`backend/tests/test_schedule_node.py`)**

```python
from datetime import date, timedelta

from app.agent.state import HierarDoState, ParsedGoal, ParsedMilestone, ParsedTodo
from app.agent.nodes.schedule import schedule_node


def _make_state(weeks: int = 4, todos_per_week: int = 3) -> HierarDoState:
    deadline = date.today() + timedelta(days=28)
    milestones = [
        ParsedMilestone(
            title=f"마일스톤 {w}",
            week_number=w,
            todos=[
                ParsedTodo(title=f"할 일 {w}-{t}", estimated_minutes=30)
                for t in range(todos_per_week)
            ],
        )
        for w in range(1, weeks + 1)
    ]
    return HierarDoState(
        raw_input="테스트",
        available_hours={"weekday": 2, "weekend": 4},
        goal=ParsedGoal(title="테스트 목표", deadline=deadline),
        milestones=milestones,
        error=None,
    )


def test_schedule_assigns_due_dates():
    state = _make_state()
    result = schedule_node(state)
    for milestone in result["milestones"]:
        for todo in milestone.todos:
            assert todo.due_date is not None, "due_date가 None이면 안 됨"


def test_schedule_due_dates_within_deadline():
    state = _make_state()
    deadline = state["goal"].deadline
    result = schedule_node(state)
    for milestone in result["milestones"]:
        for todo in milestone.todos:
            assert todo.due_date <= deadline, f"due_date {todo.due_date}가 deadline {deadline}를 초과"


def test_schedule_week1_before_week4():
    state = _make_state()
    result = schedule_node(state)
    milestones = result["milestones"]
    week1_dates = [t.due_date for t in milestones[0].todos]
    week4_dates = [t.due_date for t in milestones[3].todos]
    assert max(week1_dates) <= min(week4_dates), "1주차 날짜가 4주차보다 앞서야 함"
```

- [ ] **Step 3: 테스트 실행 - 실패 확인**

```bash
cd backend
poetry run pytest tests/test_schedule_node.py -v
```

Expected: `ModuleNotFoundError` 또는 `ImportError` (schedule_node 미구현)

- [ ] **Step 4: `backend/app/agent/nodes/schedule.py` 구현**

```python
from datetime import date, timedelta

from app.agent.state import HierarDoState, ParsedMilestone


def schedule_node(state: HierarDoState) -> dict:
    goal = state["goal"]
    milestones = state["milestones"]
    today = date.today()
    deadline = goal.deadline

    total_days = max((deadline - today).days, 28)
    days_per_week = total_days // 4

    updated: list[ParsedMilestone] = []
    for milestone in milestones:
        week_start = today + timedelta(days=(milestone.week_number - 1) * days_per_week)
        week_end = week_start + timedelta(days=days_per_week - 1)
        if week_end > deadline:
            week_end = deadline

        n = len(milestone.todos)
        span = max((week_end - week_start).days, 1)
        updated_todos = []
        for i, todo in enumerate(milestone.todos):
            offset = int(i * span / max(n - 1, 1)) if n > 1 else 0
            due = week_start + timedelta(days=offset)
            if due > deadline:
                due = deadline
            updated_todos.append(todo.model_copy(update={"due_date": due}))

        updated.append(milestone.model_copy(update={"todos": updated_todos}))

    return {"milestones": updated}
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
poetry run pytest tests/test_schedule_node.py -v
```

Expected: 3개 테스트 모두 PASSED

- [ ] **Step 6: 커밋**

```bash
git add backend/app/agent/ backend/tests/
git commit -m "feat: LangGraph 상태 및 schedule 노드 구현 (TDD)"
```

---

## Task 6: parse_goal 및 decompose 노드

**Files:**
- Create: `backend/app/agent/nodes/parse_goal.py`
- Create: `backend/app/agent/nodes/decompose.py`

- [ ] **Step 1: `backend/app/agent/nodes/parse_goal.py` 작성**

```python
import json
from datetime import date, timedelta

import anthropic

from app.agent.state import HierarDoState, ParsedGoal

_client = anthropic.Anthropic()

_SYSTEM = """You are a goal parsing assistant. Extract a structured goal from the user's natural language input.
Return ONLY a valid JSON object with exactly these fields:
- "title": concise goal title (Korean is fine, max 50 chars)
- "deadline": ISO date string YYYY-MM-DD (default to 30 days from today if not specified)

Today's date is {today}. No explanation — JSON only."""


def parse_goal_node(state: HierarDoState) -> dict:
    today = date.today().isoformat()
    default_deadline = (date.today() + timedelta(days=30)).isoformat()
    response = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        system=_SYSTEM.format(today=today),
        messages=[{"role": "user", "content": state["raw_input"]}],
    )
    raw = response.content[0].text.strip()
    # 코드 블록 제거
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    data = json.loads(raw)
    data.setdefault("deadline", default_deadline)
    return {"goal": ParsedGoal(**data)}
```

- [ ] **Step 2: `backend/app/agent/nodes/decompose.py` 작성**

```python
import json

import anthropic

from app.agent.state import HierarDoState, ParsedMilestone, ParsedTodo

_client = anthropic.Anthropic()

_SYSTEM = """You are a task decomposition assistant. Break the given goal into exactly 4 weekly milestones.
Each milestone must have 3-5 daily todos with realistic estimated_minutes (15-120).

Return ONLY a valid JSON array:
[
  {
    "title": "milestone title (Korean OK)",
    "week_number": 1,
    "todos": [
      {"title": "todo title (Korean OK)", "estimated_minutes": 30}
    ]
  }
]

No explanation — JSON array only."""


def decompose_node(state: HierarDoState) -> dict:
    goal = state["goal"]
    prompt = (
        f"Goal: {goal.title}\n"
        f"Deadline: {goal.deadline}\n"
        f"Available hours per day — weekday: {state['available_hours'].get('weekday', 2)}h, "
        f"weekend: {state['available_hours'].get('weekend', 4)}h"
    )
    response = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    data = json.loads(raw)
    milestones = [
        ParsedMilestone(
            title=m["title"],
            week_number=m["week_number"],
            todos=[ParsedTodo(**t) for t in m["todos"]],
        )
        for m in data
    ]
    return {"milestones": milestones}
```

- [ ] **Step 3: 커밋**

```bash
git add backend/app/agent/nodes/
git commit -m "feat: parse_goal, decompose LangGraph 노드 구현"
```

---

## Task 7: LangGraph 그래프 조립

**Files:**
- Create: `backend/app/agent/graph.py`

- [ ] **Step 1: `backend/app/agent/graph.py` 작성**

```python
from langgraph.graph import StateGraph, END

from app.agent.state import HierarDoState
from app.agent.nodes.parse_goal import parse_goal_node
from app.agent.nodes.decompose import decompose_node
from app.agent.nodes.schedule import schedule_node


def _build() -> object:
    graph = StateGraph(HierarDoState)
    graph.add_node("parse_goal", parse_goal_node)
    graph.add_node("decompose", decompose_node)
    graph.add_node("schedule", schedule_node)
    graph.set_entry_point("parse_goal")
    graph.add_edge("parse_goal", "decompose")
    graph.add_edge("decompose", "schedule")
    graph.add_edge("schedule", END)
    return graph.compile()


pipeline = _build()
```

- [ ] **Step 2: import 확인**

```bash
cd backend
poetry run python -c "from app.agent.graph import pipeline; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: 커밋**

```bash
git add backend/app/agent/graph.py
git commit -m "feat: LangGraph 파이프라인 조립"
```

---

## Task 8: FastAPI 메인 앱 + CORS

**Files:**
- Create: `backend/app/main.py`

- [ ] **Step 1: `backend/app/main.py` 작성**

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.init_db import init_db
from app.api.v1 import goals as goals_router
from app.api.v1 import todos as todos_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Hierar-Do API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(goals_router.router, prefix="/api/v1")
app.include_router(todos_router.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 2: 커밋**

```bash
git add backend/app/main.py
git commit -m "feat: FastAPI 앱 초기화, CORS 및 lifespan 설정"
```

---

## Task 9: Goals API 엔드포인트 (TDD)

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/v1/__init__.py`
- Create: `backend/app/api/v1/goals.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_goals_api.py`

- [ ] **Step 1: `backend/tests/conftest.py` 작성**

```python
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from unittest.mock import patch
from datetime import date, timedelta

import app.models  # noqa: F401 — 모든 테이블 등록
from app.main import app
from app.db.session import Base, get_db
from app.agent.state import ParsedGoal, ParsedMilestone, ParsedTodo

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSession = async_sessionmaker(test_engine, expire_on_commit=False)


async def override_get_db():
    async with TestSession() as session:
        yield session


@pytest.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def mock_pipeline():
    deadline = date.today() + timedelta(days=28)
    fake_result = {
        "goal": ParsedGoal(title="토익 900점 달성", deadline=deadline),
        "milestones": [
            ParsedMilestone(
                title=f"마일스톤 {w}주차",
                week_number=w,
                todos=[
                    ParsedTodo(title=f"할 일 {w}-{t}", estimated_minutes=30, due_date=deadline)
                    for t in range(3)
                ],
            )
            for w in range(1, 5)
        ],
        "error": None,
    }
    with patch("app.api.v1.goals.pipeline") as mock:
        mock.invoke.return_value = fake_result
        yield mock


@pytest.fixture
async def client():
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
```

- [ ] **Step 2: 실패할 Goals API 테스트 작성 (`backend/tests/test_goals_api.py`)**

```python
import pytest


@pytest.mark.asyncio
async def test_create_goal_returns_201(client, mock_pipeline):
    resp = await client.post(
        "/api/v1/goals",
        json={"raw_input": "이번 달 토익 900점", "available_hours": {"weekday": 2, "weekend": 4}},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "goal" in body
    assert "milestones" in body
    assert "todos" in body
    assert body["goal"]["title"] == "토익 900점 달성"
    assert len(body["milestones"]) == 4


@pytest.mark.asyncio
async def test_list_goals_empty(client):
    resp = await client.get("/api/v1/goals")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_goal_not_found(client):
    resp = await client.get("/api/v1/goals/999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_then_get_goal(client, mock_pipeline):
    create_resp = await client.post(
        "/api/v1/goals",
        json={"raw_input": "이번 달 토익 900점", "available_hours": {"weekday": 2, "weekend": 4}},
    )
    goal_id = create_resp.json()["goal"]["id"]
    get_resp = await client.get(f"/api/v1/goals/{goal_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == goal_id
```

- [ ] **Step 3: 테스트 실행 - 실패 확인**

```bash
cd backend
poetry run pytest tests/test_goals_api.py -v
```

Expected: `ImportError` 또는 404 errors (goals.py 미구현)

- [ ] **Step 4: `backend/app/api/v1/goals.py` 구현**

```python
import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agent.graph import pipeline
from app.db.session import get_db
from app.models.goal import Goal
from app.models.milestone import Milestone
from app.models.todo import Todo
from app.models.user import User
from app.schemas.goal import (
    CreateGoalRequest,
    CreateGoalResponse,
    GoalOut,
    MilestoneOut,
    TodoOut,
)

router = APIRouter(prefix="/goals", tags=["goals"])
_MVP_USER_ID = 1


async def _ensure_default_user(db: AsyncSession) -> None:
    result = await db.execute(select(User).where(User.id == _MVP_USER_ID))
    if result.scalar_one_or_none() is None:
        db.add(User(id=_MVP_USER_ID, email="default@hierardo.app"))
        await db.commit()


@router.post("", response_model=CreateGoalResponse)
async def create_goal(
    req: CreateGoalRequest, db: AsyncSession = Depends(get_db)
):
    await _ensure_default_user(db)

    state = {
        "raw_input": req.raw_input,
        "available_hours": req.available_hours,
        "goal": None,
        "milestones": [],
        "error": None,
    }
    result = await asyncio.to_thread(pipeline.invoke, state)

    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])

    parsed_goal = result["goal"]
    parsed_milestones = result["milestones"]

    goal = Goal(
        user_id=_MVP_USER_ID,
        title=parsed_goal.title,
        raw_input=req.raw_input,
        deadline=parsed_goal.deadline,
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
async def list_goals(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(
        select(Goal)
        .where(Goal.user_id == _MVP_USER_ID)
        .options(selectinload(Goal.milestones).selectinload(Milestone.todos))
        .order_by(Goal.created_at.desc())
    )
    return [GoalOut.model_validate(g) for g in rows.scalars().all()]


@router.get("/{goal_id}", response_model=GoalOut)
async def get_goal(goal_id: int, db: AsyncSession = Depends(get_db)):
    rows = await db.execute(
        select(Goal)
        .where(Goal.id == goal_id, Goal.user_id == _MVP_USER_ID)
        .options(selectinload(Goal.milestones).selectinload(Milestone.todos))
    )
    goal = rows.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return GoalOut.model_validate(goal)


@router.get("/{goal_id}/suggest", response_model=dict)
async def suggest_goal(_goal_id: int):
    return {"message": "MVP 이후 구현 예정"}


@router.post("/{goal_id}/apply", response_model=dict)
async def apply_suggestion(_goal_id: int):
    return {"message": "MVP 이후 구현 예정"}
```

- [ ] **Step 5: 빈 `__init__.py` 파일 생성**

```bash
touch backend/app/api/__init__.py backend/app/api/v1/__init__.py
```

- [ ] **Step 6: 테스트 통과 확인**

```bash
poetry run pytest tests/test_goals_api.py -v
```

Expected: 4개 테스트 모두 PASSED

- [ ] **Step 7: 커밋**

```bash
git add backend/app/api/ backend/tests/conftest.py backend/tests/test_goals_api.py
git commit -m "feat: Goals API 엔드포인트 구현 (TDD)"
```

---

## Task 10: Todos API 엔드포인트 (TDD)

**Files:**
- Create: `backend/app/api/v1/todos.py`
- Create: `backend/tests/test_todos_api.py`

- [ ] **Step 1: 실패할 Todos API 테스트 작성**

```python
import pytest


@pytest.mark.asyncio
async def test_mark_todo_done(client, mock_pipeline):
    create_resp = await client.post(
        "/api/v1/goals",
        json={"raw_input": "테스트 목표", "available_hours": {"weekday": 2, "weekend": 4}},
    )
    todos = create_resp.json()["todos"]
    todo_id = todos[0]["id"]

    resp = await client.patch(f"/api/v1/todos/{todo_id}/done")
    assert resp.status_code == 200
    assert resp.json()["is_done"] is True


@pytest.mark.asyncio
async def test_mark_todo_undone(client, mock_pipeline):
    create_resp = await client.post(
        "/api/v1/goals",
        json={"raw_input": "테스트 목표", "available_hours": {"weekday": 2, "weekend": 4}},
    )
    todo_id = create_resp.json()["todos"][0]["id"]

    await client.patch(f"/api/v1/todos/{todo_id}/done")
    resp = await client.patch(f"/api/v1/todos/{todo_id}/undone")
    assert resp.status_code == 200
    assert resp.json()["is_done"] is False


@pytest.mark.asyncio
async def test_todo_not_found(client):
    resp = await client.patch("/api/v1/todos/9999/done")
    assert resp.status_code == 404
```

- [ ] **Step 2: 테스트 실행 - 실패 확인**

```bash
poetry run pytest tests/test_todos_api.py -v
```

Expected: `ImportError` 또는 404 errors

- [ ] **Step 3: `backend/app/api/v1/todos.py` 구현**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.todo import Todo
from app.schemas.goal import TodoOut

router = APIRouter(prefix="/todos", tags=["todos"])


async def _get_todo_or_404(todo_id: int, db: AsyncSession) -> Todo:
    result = await db.execute(select(Todo).where(Todo.id == todo_id))
    todo = result.scalar_one_or_none()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo


@router.patch("/{todo_id}/done", response_model=TodoOut)
async def mark_done(todo_id: int, db: AsyncSession = Depends(get_db)):
    todo = await _get_todo_or_404(todo_id, db)
    todo.is_done = True
    await db.commit()
    await db.refresh(todo)
    return TodoOut.model_validate(todo)


@router.patch("/{todo_id}/undone", response_model=TodoOut)
async def mark_undone(todo_id: int, db: AsyncSession = Depends(get_db)):
    todo = await _get_todo_or_404(todo_id, db)
    todo.is_done = False
    await db.commit()
    await db.refresh(todo)
    return TodoOut.model_validate(todo)
```

- [ ] **Step 4: 전체 테스트 통과 확인**

```bash
poetry run pytest tests/ -v
```

Expected: 전체 PASSED (schedule 3개 + goals 4개 + todos 3개 = 10개)

- [ ] **Step 5: 커밋**

```bash
git add backend/app/api/v1/todos.py backend/tests/test_todos_api.py
git commit -m "feat: Todos API 엔드포인트 구현 (TDD)"
```

---

## Task 11: docker-compose.yml DATABASE_URL 드라이버 수정 확인

**Files:**
- Modify: `docker-compose.yml` (asyncpg 드라이버 추가)

- [ ] **Step 1: docker-compose.yml의 DATABASE_URL 확인 및 수정**

현재 `postgresql://` → `postgresql+asyncpg://`로 변경:

```yaml
# docker-compose.yml backend 서비스의 environment 항목
environment:
  DATABASE_URL: postgresql+asyncpg://hierardo:hierardo@db:5432/hierardo
  ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
```

- [ ] **Step 2: .env 파일 생성 (로컬 개발용)**

```bash
cp backend/.env.example backend/.env
# .env 파일에 실제 ANTHROPIC_API_KEY 입력
```

- [ ] **Step 3: 커밋**

```bash
git add docker-compose.yml
git commit -m "fix: docker-compose DATABASE_URL asyncpg 드라이버 지정"
```

---

## Task 12: 로컬 실행 검증

**Files:** 없음 (검증만)

- [ ] **Step 1: PostgreSQL 실행**

```bash
docker-compose up db -d
```

Expected: PostgreSQL 컨테이너 실행 중

- [ ] **Step 2: 백엔드 서버 실행**

```bash
cd backend
ANTHROPIC_API_KEY=<your_key> DATABASE_URL=postgresql+asyncpg://hierardo:hierardo@localhost:5432/hierardo \
  poetry run uvicorn app.main:app --reload --port 8000
```

Expected: `Uvicorn running on http://0.0.0.0:8000`

- [ ] **Step 3: /health 엔드포인트 확인**

```bash
curl http://localhost:8000/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 4: 목표 생성 API 확인**

```bash
curl -X POST http://localhost:8000/api/v1/goals \
  -H "Content-Type: application/json" \
  -d '{"raw_input":"이번 달 안에 토익 900점 받고 싶어","available_hours":{"weekday":2,"weekend":4}}'
```

Expected: `{"goal":{...},"milestones":[...],"todos":[...]}`

- [ ] **Step 5: 최종 커밋**

```bash
git add .
git commit -m "chore: 백엔드 MVP 구현 완료"
```
