# Hierar-Do 프로젝트 — 보완 사항 정리

## 요약

| 영역 | 발견된 문제 수 |
|------|-------------|
| 🐛 버그 / 로직 오류 | 5 |
| 🔒 보안 | 3 |
| 🏗️ 아키텍처 / 설계 | 6 |
| 🎨 프론트엔드 UX/UI | 5 |
| 🧪 테스트 | 3 |
| 📦 인프라 / DevOps | 4 |

---

## 🐛 버그 / 로직 오류

### 1. `asyncio.to_thread`로 동기 LangGraph 파이프라인 실행 — 실질적 블로킹
**파일**: [goals.py](file:///Users/User/src/repos/Hierar-Do/backend/app/api/v1/goals.py#L46)

```python
result = await asyncio.to_thread(pipeline.invoke, state)
```

`asyncio.to_thread`는 내부적으로 스레드풀을 사용하지만, LangGraph 노드(`parse_goal`, `decompose`)는 내부에서 동기 `anthropic.Anthropic()` 클라이언트를 호출합니다. 여러 요청이 동시에 들어오면 스레드 고갈 가능성이 있고, FastAPI의 비동기 이점이 사라집니다.

**해결 방법**: `AsyncAnthropic` 클라이언트를 사용하거나, LangGraph를 `async` 노드로 재구성한 후 `pipeline.ainvoke` 사용.

---

### 2. `schedule_node` — 에러 상태 무시
**파일**: [schedule.py](file:///Users/User/src/repos/Hierar-Do/backend/app/agent/nodes/schedule.py#L6)

```python
def schedule_node(state: HierarDoState) -> dict:
    goal = state["goal"]   # error 상태에서 None이면 AttributeError
    milestones = state["milestones"]
```

`decompose_node`가 에러를 반환하면 `state["goal"]`은 `None`, `state["milestones"]`는 `[]`인 채로 `schedule_node`에 진입합니다. `decompose_node`처럼 `if state.get("error") or not state.get("goal")` 가드가 없어 `AttributeError` 발생합니다.

---

### 3. `_ensure_default_user` — 레이스 컨디션
**파일**: [goals.py](file:///Users/User/src/repos/Hierar-Do/backend/app/api/v1/goals.py#L26-L30)

동시 요청 시 두 요청 모두 `user`가 없다고 판단하여 동시에 `INSERT`를 시도, `UNIQUE` 제약 위반으로 500 에러 발생 가능.

**해결 방법**: `INSERT ... ON CONFLICT DO NOTHING` 또는 애플리케이션 시작(`lifespan`)에서 한 번만 실행.

---

### 4. 달력 날짜 계산 — 타임존 불일치
**파일**: [page.tsx (dashboard)](file:///Users/User/src/repos/Hierar-Do/frontend/src/app/page.tsx#L13), [calendar/page.tsx](file:///Users/User/src/repos/Hierar-Do/frontend/src/app/calendar/page.tsx#L12-L15)

```typescript
const today = new Date().toISOString().slice(0, 10); // UTC 기준
```

`toISOString()`은 UTC 시간을 반환하므로, UTC+9(한국) 환경에서 자정 이후 9시간 동안은 "어제" 날짜가 today로 잡혀 오늘의 할 일이 표시되지 않는 버그가 있습니다.

**해결 방법**:
```typescript
const today = new Date().toLocaleDateString("sv"); // YYYY-MM-DD (로컬 타임존)
```

---

### 5. `reschedule` — 재조정 알고리즘의 평일/주말 미반영
**파일**: [reschedule.py](file:///Users/User/src/repos/Hierar-Do/backend/app/api/v1/reschedule.py#L25-L43)

재조정 시 `available_hours`(평일/주말 가용 시간)를 전혀 고려하지 않고 단순 날짜 균등 분배만 합니다. `Goal` 모델에 `available_hours`가 저장되지 않아 재조정 단계에서 사용할 수 없습니다.

---

## 🔒 보안

### 6. CORS — `allow_origins` 하드코딩
**파일**: [main.py](file:///Users/User/src/repos/Hierar-Do/backend/app/main.py#L22)

```python
allow_origins=["http://localhost:3000"],
```

프로덕션 배포 시 CORS를 환경변수로 관리하지 않아 직접 코드를 수정해야 합니다.

```python
# 권장
origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
```

---

### 7. `docker-compose.yml` — DB 비밀번호 평문 하드코딩
**파일**: [docker-compose.yml](file:///Users/User/src/repos/Hierar-Do/docker-compose.yml#L5-L7)

```yaml
POSTGRES_PASSWORD: hierardo
```

`.env` 파일을 사용하도록 변경해야 합니다.

```yaml
env_file: .env
```

---

### 8. API 엔드포인트에 입력값 검증 미흡
**파일**: [goals.py (CreateGoalRequest)](file:///Users/User/src/repos/Hierar-Do/backend/app/schemas/goal.py#L50-L52)

```python
class CreateGoalRequest(BaseModel):
    raw_input: str               # 길이 제한 없음
    available_hours: dict        # 타입 미검증
```

`raw_input`에 길이 제한이 없고, `available_hours`가 `dict` 타입으로만 선언되어 있어 `weekday`/`weekend` 키 누락 시 런타임 오류가 발생합니다.

**권장 스키마**:
```python
from pydantic import BaseModel, Field, constr

class AvailableHours(BaseModel):
    weekday: int = Field(ge=1, le=24)
    weekend: int = Field(ge=1, le=24)

class CreateGoalRequest(BaseModel):
    raw_input: str = Field(min_length=5, max_length=500)
    available_hours: AvailableHours
```

---

## 🏗️ 아키텍처 / 설계

### 9. `GoalStatus` 중복 정의
**파일**: [models/goal.py](file:///Users/User/src/repos/Hierar-Do/backend/app/models/goal.py#L11-L14), [schemas/goal.py](file:///Users/User/src/repos/Hierar-Do/backend/app/schemas/goal.py#L8-L11)

`GoalStatus` Enum이 `models/goal.py`와 `schemas/goal.py` 두 곳에 동일하게 정의되어 있습니다. 동기화 실패 시 버그가 생길 수 있습니다.

**해결 방법**: 단일 소스(`models/goal.py` 또는 별도 `enums.py`)에서 import하여 재사용.

---

### 10. DB 마이그레이션 도구 부재 (`init_db`로 `create_all` 사용)
**파일**: [init_db.py](file:///Users/User/src/repos/Hierar-Do/backend/app/db/init_db.py)

`Base.metadata.create_all`은 개발 초기에는 편리하지만, 스키마 변경 시 기존 테이블을 수정하지 못합니다. 컬럼 추가/변경이 반영되지 않아 프로덕션 데이터 손실 위험이 있습니다.

**해결 방법**: [Alembic](https://alembic.sqlalchemy.org/) 도입.

---

### 11. `_MVP_USER_ID = 1` 상수 중복 정의
**파일**: [goals.py](file:///Users/User/src/repos/Hierar-Do/backend/app/api/v1/goals.py#L23), [reschedule.py](file:///Users/User/src/repos/Hierar-Do/backend/app/api/v1/reschedule.py#L15)

같은 상수가 두 파일에 각각 정의되어 있습니다. 공통 상수 파일(`app/constants.py`)로 분리 권장.

---

### 12. LLM 응답 파싱 — 정규식 의존성 취약
**파일**: [parse_goal.py](file:///Users/User/src/repos/Hierar-Do/backend/app/agent/nodes/parse_goal.py#L27-L28), [decompose.py](file:///Users/User/src/repos/Hierar-Do/backend/app/agent/nodes/decompose.py#L43-L44)

```python
raw = re.sub(r"^```(?:json)?\s*", "", raw)
raw = re.sub(r"\s*```$", "", raw)
```

LLM이 마크다운 코드블럭 없이 JSON을 바로 반환하거나, 앞뒤에 설명 텍스트를 추가하는 경우 파싱이 실패합니다.

**해결 방법**: Anthropic의 structured output(tool use / `response_format`)을 사용하거나 JSON 추출 로직을 더 견고하게 구성.

---

### 13. 목표 생성 중 DB 저장 실패 시 롤백 미처리
**파일**: [goals.py](file:///Users/User/src/repos/Hierar-Do/backend/app/api/v1/goals.py#L60-L83)

LLM 호출 성공 후 DB 저장 중 예외가 발생하면 세션이 자동 롤백되지만, LLM API 비용이 이미 발생한 상태입니다. 재시도 시 중복 LLM 호출이 발생할 수 있습니다.

---

### 14. `available_hours`가 DB에 저장되지 않음
**파일**: [models/goal.py](file:///Users/User/src/repos/Hierar-Do/backend/app/models/goal.py)

목표 생성 시 입력한 `available_hours` (평일/주말 가용 시간)가 `Goal` 모델에 저장되지 않습니다. 재조정 기능이나 향후 AI 재제안 시 사용자의 실제 가용 시간을 알 수 없습니다.

---

## 🎨 프론트엔드 UX/UI

### 15. 목표 생성 중 전체 페이지 상호작용 차단 없음
**파일**: [GoalModal.tsx](file:///Users/User/src/repos/Hierar-Do/frontend/src/components/GoalModal.tsx#L94-L100)

목표 생성(`isPending`) 중 버튼만 비활성화되지만, 모달 닫기(`Escape` 키, 백드롭 클릭)는 여전히 가능합니다. 생성 중 모달을 닫으면 결과를 알 수 없는 UX 문제가 발생합니다.

---

### 16. 에러 피드백 단순화
**파일**: [GoalModal.tsx](file:///Users/User/src/repos/Hierar-Do/frontend/src/components/GoalModal.tsx#L102-L106), [api.ts](file:///Users/User/src/repos/Hierar-Do/frontend/src/lib/api.ts#L8)

```typescript
if (!res.ok) throw new Error(`API error: ${res.status}`);
```

HTTP 상태 코드만 표시하고 백엔드의 실제 에러 메시지(`detail`)를 사용자에게 보여주지 않습니다. LLM 파싱 실패 등 구체적인 원인을 사용자가 알기 어렵습니다.

---

### 17. 하단 네비게이션 — 비활성 탭 기능 없음
**파일**: [page.tsx](file:///Users/User/src/repos/Hierar-Do/frontend/src/app/page.tsx#L231-L260)

"브리핑", "설정" 탭이 클릭 가능한 UI이지만 아무 동작도 하지 않습니다. 사용자가 탭을 클릭했을 때 아무 반응이 없어 앱이 고장난 것처럼 느껴질 수 있습니다.

**해결 방법**: 미구현 탭은 `opacity-30`이나 `pointer-events-none` 처리 또는 "준비 중" 토스트 메시지 표시.

---

### 18. 로딩 스피너 없음
**파일**: [page.tsx](file:///Users/User/src/repos/Hierar-Do/frontend/src/app/page.tsx#L48-L51)

```tsx
로딩 중...
```

단순 텍스트만 표시되고 시각적 스피너/스켈레톤 UI가 없어 UX가 투박합니다.

---

### 19. 모바일 — 상단 헤더 "메뉴" 아이콘이 실제로 캘린더 링크
**파일**: [page.tsx](file:///Users/User/src/repos/Hierar-Do/frontend/src/app/page.tsx#L26-L30)

```tsx
<Link href="/calendar" aria-label="캘린더 보기">
  <span className="material-symbols-outlined">menu</span>
```

`menu` 아이콘이지만 캘린더로 이동합니다. 사용자는 메뉴 아이콘을 클릭하면 드로어나 사이드바가 열릴 것으로 예상하므로 혼란을 줍니다.

---

## 🧪 테스트

### 20. LLM 호출 노드(`parse_goal`, `decompose`)에 대한 단위 테스트 없음
**파일**: [backend/tests/](file:///Users/User/src/repos/Hierar-Do/backend/tests/)

현재 `test_schedule_node.py`만 존재하고 LLM 노드 테스트가 없습니다. `anthropic.Anthropic`을 모킹하여 JSON 파싱 로직, 에러 처리를 검증하는 테스트가 필요합니다.

---

### 21. 프론트엔드 테스트 완전 부재
**파일**: [frontend/](file:///Users/User/src/repos/Hierar-Do/frontend/)

Jest/Vitest + React Testing Library 설정이 전혀 없습니다. `GoalModal`, `useToggleTodo`, `useCreateGoal` 등 핵심 상호작용에 대한 컴포넌트 테스트가 필요합니다.

---

### 22. `test_goals_api.py` — LLM 호출을 실제로 하지 않는지 확인 불명확
현재 테스트가 실제 LLM API를 호출하는지, 모킹하는지 `conftest.py`만으로는 불명확합니다. CI에서 비용이 발생할 수 있습니다.

---

## 📦 인프라 / DevOps

### 23. `docker-compose` 프론트엔드 — `NEXT_PUBLIC_API_URL` 이슈
**파일**: [docker-compose.yml](file:///Users/User/src/repos/Hierar-Do/docker-compose.yml#L37)

```yaml
NEXT_PUBLIC_API_URL: http://localhost:8000
```

Docker 컨테이너 내부에서 `localhost`는 백엔드 컨테이너가 아닌 프론트엔드 컨테이너 자신을 가리킵니다. 브라우저에서 실행되는 Next.js 클라이언트 사이드 코드는 이 값을 사용하므로 실제 브라우저가 `http://localhost:8000`에 접근할 수 있어야 합니다. 서버 사이드 렌더링(SSR)을 추가할 경우 컨테이너 내부 통신을 위해 `http://backend:8000`을 별도로 설정해야 합니다.

---

### 24. `backend/Dockerfile` — `requirements.txt`와 `pyproject.toml` 이중 관리
**파일**: [backend/requirements.txt](file:///Users/User/src/repos/Hierar-Do/backend/requirements.txt), [backend/pyproject.toml](file:///Users/User/src/repos/Hierar-Do/backend/pyproject.toml)

`pyproject.toml`(Poetry)과 `requirements.txt` 두 가지로 의존성이 이중 관리되고 있습니다. 한쪽을 업데이트하면 다른 쪽과 불일치가 생길 수 있습니다.

**해결 방법**: Dockerfile에서 `poetry install --no-dev` 사용 또는 `requirements.txt`를 자동 생성(`poetry export`).

---

### 25. 환경변수 `.env.example` 미완성
**파일**: [backend/.env.example](file:///Users/User/src/repos/Hierar-Do/backend/.env.example)

`ANTHROPIC_API_KEY` 등 필수 환경변수 목록과 설명이 부족합니다. 신규 개발자가 프로젝트를 처음 세팅할 때 어떤 값을 설정해야 하는지 안내가 필요합니다.

---

### 26. `README.md` 거의 비어있음
**파일**: [README.md](file:///Users/User/src/repos/Hierar-Do/README.md)

루트 `README.md`가 2바이트(사실상 비어있음)입니다. 프로젝트 소개, 로컬 실행 방법, 환경변수 설정 가이드 등의 내용이 필요합니다.

---

## 우선순위별 정리

| 우선순위 | 항목 |
|---------|------|
| 🔴 즉시 수정 | #2 schedule_node 에러 가드, #4 타임존 버그, #3 레이스 컨디션, #8 입력값 검증 |
| 🟠 단기 개선 | #1 비동기 LLM 클라이언트, #10 Alembic 도입, #14 available_hours DB 저장, #6 CORS 환경변수화 |
| 🟡 중기 개선 | #9 GoalStatus 중복, #15~19 UX 개선, #20~21 테스트 추가, #23~24 Docker 정리 |
| 🟢 장기 / MVP 이후 | #12 LLM structured output, #13 트랜잭션 개선, #5 재조정 알고리즘 고도화 |
