# Hierar-Do

> 월간 목표를 자연어로 입력하면 AI 에이전트가 주간 마일스톤 → 일일 할 일로 자동 분해해주는 계층형 목표 관리 서비스

단순 기록 도구가 아니라 사용자의 **가용 시간을 고려해 실행 가능한 일정을 생성**하고, 진척도에 따라 **스스로 재조정 제안**하는 반능동형 AI 에이전트 서비스입니다.

---

## Demo

```
입력: "이번 달 안에 토익 900점 받고 싶어 (평일 2시간, 주말 4시간 가능)"

출력:
├── Goal: 토익 900점 달성  (deadline: 2026-05-31)
│   ├── Week 1: 파트 5 문법 정리
│   │   ├── 동사 시제 20문제       (30분, 5/5)
│   │   └── 접속사 패턴 정리       (40분, 5/6)
│   ├── Week 2: RC 독해 속도 향상
│   │   └── ...
│   └── Week 3 / 4: ...
│
│   [AI 브리핑] "Week 1 완료율 40% — 이 속도면 3주차가 위험해요.
│               주말에 1시간 추가 확보하거나 Week 2 범위를 줄이는 걸 추천합니다."
```

---

## Features

- **자연어 목표 입력** — "토익 900점 받고 싶어 (평일 2시간)" 그대로 입력, AI가 파싱
- **계층형 자동 분해** — 월간 목표 → 주간 마일스톤 4개 → 일일 할 일 (소요 시간 산정 포함)
- **가용 시간 기반 스케줄링** — 평일/주말 가용 시간을 고려한 due_date 배분 및 과부하 검증
- **진척도 기반 스마트 재조정** — 완료율·지연 패턴을 분석해 재배치 제안 생성
- **AI 브리핑 스트리밍** — 오늘의 할 일과 위험 구간을 SSE로 실시간 브리핑
- **수동 편집 지원** — AI 제안을 승인하거나 직접 수정 가능한 반능동형 패턴

---

## Tech Stack

| 영역 | 기술 |
|------|------|
| Backend | FastAPI · Python · Poetry |
| AI Pipeline | LangGraph · Claude API (claude-sonnet-4-6) |
| Database | PostgreSQL · pgvector · SQLAlchemy |
| Frontend | Next.js (App Router) · TypeScript · Tailwind CSS · shadcn/ui |
| Data Fetching | TanStack Query v5 |
| Infra | Docker · docker-compose |
| CI/CD | GitHub Actions |

---

## Architecture

### 목표 생성 파이프라인 (LangGraph)

```
raw_input + available_hours
         │
         ▼
   [parse_goal]    Claude API — 자연어 → 목표 제목, 마감일, 카테고리 파싱
         │
         ▼
   [decompose]     Claude API — 목표 → 주간 마일스톤 4개 + 일일 할 일 생성
         │                      estimated_minutes(소요 시간) 산정 포함
         ▼
   [schedule]      Pure Python — 가용 시간 기반 due_date 배분 및 과부하 검증
         │
         ▼
   [store]         DB Write — Goal / Milestone / Todo 저장
```

LLM 호출은 `parse_goal`, `decompose` 두 노드만 — `schedule`은 순수 Python으로 비용 효율화.

### 재조정 파이프라인 (LangGraph)

```
goal_id
   │
   ▼
[analyze_progress]   완료율, 지연 할 일, 예상 vs 실제 소요 시간 분석
   │
   ▼
[smart_reschedule]   Claude API — 남은 기간 + 패턴 고려한 재배치 제안
                     "이 속도면 3주차가 위험해요" 식 컨텍스트 있는 코멘트 포함
```

### Data Model

```
User
└── Goal (월간 목표)
    └── Milestone (주간 마일스톤, 4개)
        └── Todo (일일 할 일, N개)
```

| 모델 | 주요 필드 |
|------|----------|
| `Goal` | `raw_input`, `title` (AI 파싱), `deadline`, `status` (pending/active/done), `available_hours_weekday/weekend` |
| `Milestone` | `week_number` (1~4), `suggested_by_ai` |
| `Todo` | `due_date`, `estimated_minutes`, `actual_minutes`, `is_done`, `suggested_by_ai` |

---

## Getting Started

### Prerequisites

- Docker & docker-compose
- [Anthropic API Key](https://console.anthropic.com/)

### 실행 (Docker)

```bash
git clone https://github.com/Je-hye/Hierar-Do.git
cd Hierar-Do

# 환경변수 설정
cp backend/.env.example backend/.env
# ANTHROPIC_API_KEY, DATABASE_URL, JWT_SECRET_KEY 입력

# 실행
docker-compose up --build
```

| 서비스 | 주소 |
|--------|------|
| 프론트엔드 | http://localhost:3000 |
| 백엔드 API | http://localhost:8000 |
| API 문서 (Swagger) | http://localhost:8000/docs |

### 로컬 실행

```bash
# 백엔드
cd backend
poetry install
poetry run uvicorn app.main:app --reload --port 8000

# 프론트엔드 (별도 터미널)
cd frontend
npm install
npm run dev
```

### 테스트

```bash
# 백엔드
cd backend && poetry run pytest

# 프론트엔드
cd frontend && npm run test
```

---

## API

### 목표

| Method | Path | 설명 |
|--------|------|------|
| `POST` | `/api/v1/goals` | 목표 생성 + 파이프라인 실행 |
| `GET` | `/api/v1/goals` | 목표 목록 |
| `GET` | `/api/v1/goals/{id}` | 목표 상세 (Milestone + Todo 포함) |
| `PATCH` | `/api/v1/goals/{id}/status` | 목표 상태 변경 (pending/active/done) |
| `DELETE` | `/api/v1/goals/{id}` | 목표 삭제 (cascade) |
| `GET` | `/api/v1/goals/{id}/suggest` | AI 재조정 제안 조회 |
| `POST` | `/api/v1/goals/{id}/apply` | AI 제안 적용 |
| `POST` | `/api/v1/goals/{id}/reschedule/smart` | 스마트 재조정 실행 |

### 할 일 & 마일스톤

| Method | Path | 설명 |
|--------|------|------|
| `POST` | `/api/v1/todos` | 할 일 직접 추가 |
| `PATCH` | `/api/v1/todos/{id}` | 할 일 수정 (제목, 날짜, 예상 시간) |
| `PATCH` | `/api/v1/todos/{id}/done` | 할 일 완료 |
| `PATCH` | `/api/v1/todos/{id}/undone` | 할 일 미완료 |
| `DELETE` | `/api/v1/todos/{id}` | 할 일 삭제 |
| `PATCH` | `/api/v1/milestones/{id}` | 마일스톤 수정 |

### 재조정 & 브리핑

| Method | Path | 설명 |
|--------|------|------|
| `POST` | `/api/v1/reschedule/preview` | 재조정 미리보기 |
| `POST` | `/api/v1/reschedule/apply` | 재조정 적용 |
| `GET` | `/api/v1/briefing` | 오늘의 AI 브리핑 (SSE 스트리밍) |

**Request 예시:**

```json
POST /api/v1/goals
{
  "raw_input": "이번 달 안에 토익 900점 받고 싶어",
  "available_hours": { "weekday": 2, "weekend": 4 }
}
```

---

## Project Structure

```
hierar-do/
├── backend/
│   └── app/
│       ├── main.py
│       ├── api/v1/
│       │   ├── auth.py             # 인증 (JWT + Google OAuth)
│       │   ├── goals.py            # 목표 CRUD + AI 파이프라인
│       │   ├── todos.py            # 할 일 CRUD
│       │   ├── milestones.py       # 마일스톤 수정
│       │   ├── reschedule.py       # 재조정 preview/apply
│       │   └── briefing.py         # AI 브리핑 (SSE)
│       ├── agent/
│       │   ├── graph.py            # 목표 생성 LangGraph 파이프라인
│       │   ├── reschedule_graph.py # 재조정 LangGraph 파이프라인
│       │   ├── state.py            # HierarDoState TypedDict
│       │   ├── embeddings.py       # pgvector 임베딩 유틸
│       │   └── nodes/
│       │       ├── parse_goal.py
│       │       ├── decompose.py
│       │       ├── schedule.py
│       │       ├── analyze_progress.py
│       │       └── smart_reschedule.py
│       ├── models/                 # SQLAlchemy ORM
│       ├── schemas/                # Pydantic 스키마
│       └── db/
├── frontend/
│   └── src/
│       ├── app/                    # Next.js App Router
│       │   ├── page.tsx            # 대시보드
│       │   ├── calendar/           # 캘린더 뷰
│       │   ├── briefing/           # AI 브리핑 페이지
│       │   ├── login/
│       │   └── register/
│       ├── components/
│       │   ├── GoalModal.tsx
│       │   ├── MonthCalendar.tsx
│       │   ├── WeekDetail.tsx
│       │   ├── RescheduleModal.tsx
│       │   └── ActualTimeModal.tsx
│       └── lib/
├── docs/
│   ├── roadmap.md                  # Phase별 로드맵 + 기술 부채
│   ├── specs/                      # 기능별 설계 스펙
│   └── plans/                      # 기능별 구현 플랜
└── docker-compose.yml
```

---

## Roadmap

자세한 내용은 [docs/roadmap.md](docs/roadmap.md)를 참고하세요.

| 상태 | 항목 |
|------|------|
| ✅ | 목표 생성 AI 파이프라인 (LangGraph) |
| ✅ | 가용 시간 기반 스케줄링 |
| ✅ | 할 일 / 마일스톤 수동 편집 |
| ✅ | JWT 인증 + Google OAuth |
| ✅ | AI 재조정 (suggest / apply) |
| ✅ | 스마트 재조정 (진척도 기반) |
| ✅ | AI 브리핑 SSE 스트리밍 |
| 🚧 | 목표 완료율 시각화 |
| 🚧 | pgvector 기반 과거 패턴 개인화 |
| 🚧 | Google Calendar 연동 |
| 🚧 | PWA 전환 |

---

## License

MIT
