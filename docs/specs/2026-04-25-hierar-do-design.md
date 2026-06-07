# Hierar-Do — Design Spec
**Date:** 2026-04-25  
**Status:** Approved

---

## Overview

Hierar-Do는 사용자의 월간 목표를 AI 에이전트가 자동으로 주간 마일스톤과 일일 할 일로 분해해주는 계층적 To-do 서비스다. 단순 기록 도구가 아니라, 사용자의 가용 시간을 고려해 실행 가능한 일정을 생성하는 것이 핵심이다.

---

## Target User

개인 사용자 (혼자 목표를 관리하는 직장인/학생). MVP에서는 인증 없이 단일 사용자(`user_id=1`) 고정으로 처리한다.

---

## Core Requirements (MVP)

1. **목표 입력** — 자연어로 월간 목표와 가용 시간을 입력
2. **자동 분해** — AI 에이전트가 목표를 주간 마일스톤 4개, 각 마일스톤당 일일 할 일로 분해
3. **할 일 체크** — 생성된 할 일을 완료/미완료로 표시

MVP에서 제외되는 것: 사용자 인증, Google Calendar 연동, 진척률 시각화, 알림

---

## Architecture

**Stack:** FastAPI + LangGraph + Claude API + PostgreSQL

**접근법:** Pipeline형 LangGraph (선형 노드 체인). 각 노드가 독립적인 역할을 가지며, 추후 멀티에이전트 패턴으로 자연스럽게 확장 가능하다.

### 에이전트 능동성

반능동형(Semi-active): AI가 제안을 생성하고, 사용자가 승인/거절한다. MVP에서는 초기 생성만 구현하고, 재조정 제안(suggest/apply)은 API 엔드포인트를 정의해두되 로직은 이후 구현한다.

---

## Project Structure

```
hierar-do/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── goals.py
│   │   │       └── todos.py
│   │   ├── agent/
│   │   │   ├── graph.py
│   │   │   ├── nodes/
│   │   │   │   ├── parse_goal.py
│   │   │   │   ├── decompose.py
│   │   │   │   └── schedule.py
│   │   │   └── state.py
│   │   ├── models/
│   │   │   ├── goal.py
│   │   │   └── user.py
│   │   ├── schemas/
│   │   │   └── goal.py
│   │   └── db/
│   │       └── session.py
├── docs/
│   └── tech_stack.md
├── pyproject.toml
├── Dockerfile
└── docker-compose.yml
```

---

## Data Model

### User
| 필드 | 타입 | 설명 |
|------|------|------|
| id | int | PK |
| email | str | 사용자 이메일 |
| available_hours | JSON | `{"weekday": 2, "weekend": 4}` (시간/일) |

### Goal (월간 목표)
| 필드 | 타입 | 설명 |
|------|------|------|
| id | int | PK |
| user_id | int | FK → User |
| title | str | AI가 파싱한 목표 제목 |
| raw_input | str | 사용자 원문 입력 |
| deadline | date | 목표 마감일 |
| status | enum | pending / active / done |
| created_at | datetime | 생성 시각 |

### Milestone (주간 마일스톤)
| 필드 | 타입 | 설명 |
|------|------|------|
| id | int | PK |
| goal_id | int | FK → Goal |
| title | str | 마일스톤 제목 |
| week_number | int | 1~4주차 |
| status | enum | pending / active / done |
| suggested_by_ai | bool | AI 제안 여부 |

### Todo (일일 할 일)
| 필드 | 타입 | 설명 |
|------|------|------|
| id | int | PK |
| milestone_id | int | FK → Milestone |
| title | str | 할 일 제목 |
| due_date | date | 수행 날짜 |
| estimated_minutes | int | AI 추정 소요 시간 |
| is_done | bool | 완료 여부 |
| suggested_by_ai | bool | AI 제안 여부 |

---

## LangGraph Pipeline

```
raw_input + available_hours
         │
         ▼
   [parse_goal]     Claude API — 자연어 → GoalSchema (title, deadline, category)
         │
         ▼
   [decompose]      Claude API — Goal → 4 Milestones + N Todos per milestone
         │                       estimated_minutes 산정 포함
         ▼
   [schedule]       Pure Python — Todo를 due_date에 배분
         │                        deadline 역산, 가용 시간 초과 검증
         ▼
   [store]          DB Write — Goal/Milestone/Todo 저장 (suggested_by_ai=True)
         │
         ▼
    API Response (계층 구조 JSON)
```

### LangGraph State

```python
class HierarDoState(TypedDict):
    raw_input: str
    available_hours: dict          # {"weekday": int, "weekend": int}
    goal: GoalSchema | None
    milestones: list[MilestoneSchema]
    todos: list[TodoSchema]
    error: str | None
```

LLM 호출은 `parse_goal`, `decompose` 노드만. `schedule`은 순수 Python 로직으로 비용 효율을 높인다.

---

## API Endpoints

| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/v1/goals` | 목표 생성 (파이프라인 트리거) |
| GET | `/api/v1/goals` | 목표 목록 조회 |
| GET | `/api/v1/goals/{id}` | 목표 상세 (Milestone + Todo 포함) |
| PATCH | `/api/v1/todos/{id}/done` | 할 일 완료 처리 |
| PATCH | `/api/v1/todos/{id}/undone` | 할 일 미완료 처리 |
| GET | `/api/v1/goals/{id}/suggest` | AI 재조정 제안 요청 (MVP 이후) |
| POST | `/api/v1/goals/{id}/apply` | AI 제안 승인 (MVP 이후) |

### POST /api/v1/goals 예시

```json
// Request
{
  "raw_input": "이번 달 안에 토익 900점 받고 싶어",
  "available_hours": { "weekday": 2, "weekend": 4 }
}

// Response
{
  "goal": { "id": 1, "title": "토익 900점 달성", "deadline": "2026-05-25" },
  "milestones": [
    { "id": 1, "title": "파트 5 문법 정리", "week_number": 1 }
  ],
  "todos": [
    { "id": 1, "title": "동사 시제 20문제", "due_date": "2026-04-27", "estimated_minutes": 30 }
  ]
}
```

---

## Future Extensions (MVP 이후)

- 사용자 인증 (JWT 기반)
- Google Calendar API 연동으로 가용 시간 자동 파악
- 진척률 시각화 (Goal별 완료율)
- 에이전트 재조정 제안 (suggest/apply 엔드포인트 구현)
- pgvector를 활용한 과거 목표 패턴 기반 개인화
