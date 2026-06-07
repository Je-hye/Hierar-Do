# CLAUDE.md

이 파일은 이 저장소에서 작업하는 Claude Code(claude.ai/code)에게 가이드를 제공합니다.

## 프로젝트 개요

**Hierar-Do**는 AI 에이전트가 사용자의 월간 목표를 주간 마일스톤과 일일 할 일로 자동 분해해주는 계층적 To-do 앱이다. 사용자가 자연어 목표와 가용 시간을 입력하면 LangGraph 파이프라인이 실행 가능한 일정으로 변환한다.

MVP 범위: 단일 사용자(`user_id=1`), 인증 없음. 반능동형 에이전트 패턴 — AI가 제안하고 사용자가 승인.

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| 백엔드 | FastAPI (비동기 Python) + LangGraph |
| LLM | Claude API (Anthropic SDK) — claude-sonnet-4-6 이상 |
| 데이터베이스 | PostgreSQL + pgvector |
| 패키지 매니저 | Poetry |
| 프론트엔드 | Next.js (App Router) + TypeScript + Tailwind CSS + shadcn/ui |
| 데이터 페칭 | TanStack Query v5 |
| 개발 환경 | Docker + Docker Compose |

## 명령어 (스캐폴딩 후)

```bash
# 백엔드
cd backend
poetry install
poetry run uvicorn app.main:app --reload --port 8000

# 프론트엔드
cd frontend
npm install
npm run dev

# 풀스택
docker-compose up
```

## 아키텍처

### LangGraph 파이프라인

```
raw_input + available_hours
         │
         ▼
   [parse_goal]   Claude API — 자연어 → GoalSchema (title, deadline)
         │
         ▼
   [decompose]    Claude API — Goal → 마일스톤 4개 + 마일스톤별 Todo (estimated_minutes 포함)
         │
         ▼
   [schedule]     순수 Python — Todo를 due_date에 배분, available_hours 초과 검증
         │
         ▼
   [store]        DB 저장 — Goal/Milestone/Todo (suggested_by_ai=True)
         │
         ▼
    API 응답 (계층 구조 JSON)
```

LLM 호출은 `parse_goal`과 `decompose` 노드만. `schedule`은 비용 절감을 위해 순수 Python 로직으로 처리.

### LangGraph 상태

```python
class HierarDoState(TypedDict):
    raw_input: str
    available_hours: dict          # {"weekday": int, "weekend": int}
    goal: GoalSchema | None
    milestones: list[MilestoneSchema]
    todos: list[TodoSchema]
    error: str | None
```

### 데이터 모델 계층

`User → Goal (월간) → Milestone (주간, 목표당 4개) → Todo (일간)`

주요 필드:
- `Goal`: `raw_input`, `title` (AI 파싱), `deadline`, `status` (pending/active/done)
- `Milestone`: `week_number` (1~4), `suggested_by_ai`
- `Todo`: `due_date`, `estimated_minutes`, `is_done`, `suggested_by_ai`

### 계획된 프로젝트 구조

```
hierar-do/
├── backend/
│   └── app/
│       ├── main.py
│       ├── api/v1/         # goals.py, todos.py
│       ├── agent/
│       │   ├── graph.py    # LangGraph 파이프라인 조립
│       │   ├── state.py    # HierarDoState TypedDict
│       │   └── nodes/      # parse_goal.py, decompose.py, schedule.py
│       ├── models/         # SQLAlchemy ORM 모델
│       ├── schemas/        # Pydantic 스키마
│       └── db/session.py
├── frontend/
│   └── src/
│       ├── app/            # Next.js App Router 페이지
│       └── lib/api.ts      # FastAPI를 향하는 Axios/fetch 인스턴스
└── docker-compose.yml
```

## API 명세

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/v1/goals` | 파이프라인 실행, Goal + Milestone + Todo 생성 |
| GET | `/api/v1/goals` | 목표 목록 조회 |
| GET | `/api/v1/goals/{id}` | 목표 상세 (Milestone + Todo 포함) |
| PATCH | `/api/v1/todos/{id}/done` | 할 일 완료 처리 |
| PATCH | `/api/v1/todos/{id}/undone` | 할 일 미완료 처리 |
| GET | `/api/v1/goals/{id}/suggest` | AI 재조정 제안 요청 (MVP 이후) |
| POST | `/api/v1/goals/{id}/apply` | AI 제안 승인 (MVP 이후) |

POST `/api/v1/goals` 요청 예시:
```json
{ "raw_input": "이번 달 안에 토익 900점 받고 싶어", "available_hours": { "weekday": 2, "weekend": 4 } }
```

## 주요 설계 결정

- **목표당 LLM 호출 2회** — `parse_goal`이 구조화된 목표 데이터 추출, `decompose`가 전체 마일스톤/Todo 트리 생성. `schedule`은 비용 절감을 위해 순수 Python.
- **파이프라인형 LangGraph** — 선형 노드 체인. 추후 멀티에이전트 패턴으로 자연스럽게 확장 가능.
- **`suggested_by_ai=True`** — AI가 생성한 모든 마일스톤과 Todo에 표시. 향후 사용자 편집 워크플로우를 위한 플래그.
- **MVP 제외 항목**: 인증, Google Calendar 연동, 진척률 시각화, suggest/apply 엔드포인트 (스텁만 정의).
- **pgvector** — 향후 과거 목표 패턴 기반 개인화를 위해 예약.

## 문서 구조

| 경로 | 내용 |
|------|------|
| `docs/roadmap.md` | Phase별 기능 로드맵 + 기술 부채 목록 |
| `docs/issues.md` | 코드 리뷰 보완 사항 (버그/보안/아키텍처/UX/테스트) |
| `docs/specs/` | 기능별 설계 스펙 |
| `docs/plans/` | 기능별 구현 플랜 |
| `docs/stitch/` | UI 디자인 목업 (대시보드, 캘린더) |

## 스킬 경로 오버라이드

Specs: docs/specs/
Plans: docs/plans/
