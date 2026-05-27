# Hierar-Do

월간 목표를 자연어로 입력하면 AI 에이전트가 주간 마일스톤 → 일일 할 일로 자동 분해해주는 계층형 Todo 서비스.

단순 기록 도구가 아니라 사용자의 가용 시간을 고려해 **실행 가능한 일정을 생성**하는 것이 핵심입니다.

---

## Demo

```
입력: "이번 달 안에 토익 900점 받고 싶어 (평일 2시간, 주말 4시간 가능)"

출력:
├── Goal: 토익 900점 달성 (deadline: 2026-05-25)
│   ├── Week 1: 파트 5 문법 정리
│   │   ├── 동사 시제 20문제 (30분, 4/27)
│   │   └── 접속사 패턴 정리 (40분, 4/28)
│   ├── Week 2: RC 독해 속도 향상
│   └── ...
```

---

## Tech Stack

| 영역 | 기술 |
|------|------|
| Backend | FastAPI, Python |
| AI Pipeline | LangGraph, Claude API (claude-sonnet) |
| Database | PostgreSQL, SQLAlchemy |
| Frontend | Next.js, TypeScript, Tailwind CSS |
| Infra | Docker, docker-compose |
| CI/CD | GitHub Actions (PR Agent) |

---

## Architecture

### AI Pipeline (LangGraph)

자연어 입력을 받아 4단계 파이프라인으로 처리합니다.

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

LLM 호출은 `parse_goal`, `decompose` 노드만 — `schedule`은 순수 Python으로 비용 효율화.

### Data Model

```
Goal (월간 목표)
└── Milestone (주간 마일스톤, 4개)
    └── Todo (일일 할 일, N개)
```

---

## API

| Method | Path | 설명 |
|--------|------|------|
| `POST` | `/api/v1/goals` | 목표 생성 + 파이프라인 실행 |
| `GET` | `/api/v1/goals` | 목표 목록 |
| `GET` | `/api/v1/goals/{id}` | 목표 상세 (Milestone + Todo 포함) |
| `PATCH` | `/api/v1/todos/{id}/done` | 할 일 완료 |
| `PATCH` | `/api/v1/todos/{id}/undone` | 할 일 미완료 |

**Request 예시:**
```json
POST /api/v1/goals
{
  "raw_input": "이번 달 안에 토익 900점 받고 싶어",
  "available_hours": { "weekday": 2, "weekend": 4 }
}
```

---

## Getting Started

### Prerequisites
- Docker & docker-compose
- Claude API Key

### 실행

```bash
git clone https://github.com/EunHye-03/Hierar-Do.git
cd Hierar-Do

# 환경변수 설정
cp backend/.env.example backend/.env
# ANTHROPIC_API_KEY 입력

# 실행
docker-compose up --build
```

백엔드: `http://localhost:8000`  
API 문서: `http://localhost:8000/docs`

### 로컬 백엔드 단독 실행

```bash
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

### 테스트

```bash
cd backend
pytest
```

---

## Project Structure

```
hierar-do/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/v1/
│   │   │   ├── goals.py
│   │   │   └── todos.py
│   │   ├── agent/
│   │   │   ├── graph.py
│   │   │   ├── state.py
│   │   │   └── nodes/
│   │   │       ├── parse_goal.py
│   │   │       ├── decompose.py
│   │   │       └── schedule.py
│   │   ├── models/
│   │   └── db/
│   └── pyproject.toml
├── frontend/
├── docker-compose.yml
└── docs/
```

---

## Roadmap

- [ ] 사용자 인증 (JWT)
- [ ] Google Calendar 연동 (가용 시간 자동 파악)
- [ ] 진척률 시각화
- [ ] AI 재조정 제안 (`suggest` / `apply` 엔드포인트)
- [ ] pgvector 기반 과거 목표 패턴 개인화
