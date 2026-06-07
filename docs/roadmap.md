# Hierar-Do 고도화 로드맵

> **현재 상태**: MVP 완성 + 코드 품질 개선 완료  
> **다음 목표**: 실제 사용 가능한 서비스로 성장

---

## Phase 1 — UX 완성 & 핵심 기능 보완
> *지금 당장 사용성에 직결되는 것들*

### 1-1. 목표/할 일 수동 편집
현재는 AI가 생성한 것을 수정할 방법이 없습니다.

**백엔드 추가 API**
- `PATCH /api/v1/todos/{id}` — 제목, 날짜, 예상 시간 수정
- `PATCH /api/v1/milestones/{id}` — 마일스톤 제목 수정
- `DELETE /api/v1/goals/{id}` — 목표 삭제 (cascade)
- `POST /api/v1/goals/{id}/todos` — 할 일 직접 추가

**프론트엔드**
- 마일스톤/할 일 인라인 편집 UI (클릭 → 입력 필드 전환)
- 목표 삭제 확인 모달
- 할 일 직접 추가 버튼

---

### 1-2. 목표 완료 처리 & 진척률 시각화
현재 `Goal.status`는 `active`만 사용되고 있습니다.

**백엔드**
- `PATCH /api/v1/goals/{id}/status` — `pending` / `active` / `done` 전환
- 모든 Todo 완료 시 Goal 자동 `done` 처리 (이벤트 훅 또는 별도 API)

**프론트엔드**
- 대시보드 목표 카드에 전체 완료율 표시 (진척 바)
- 완료된 목표는 별도 섹션으로 분리 ("완료된 목표")
- 마일스톤 완료율 → `Milestone.status` 자동 업데이트

---

### 1-3. AI 재조정 제안 (suggest/apply 엔드포인트 구현)
현재 `GET /api/v1/goals/{id}/suggest`는 스텁만 존재합니다. 설계 스펙에 이미 정의된 기능입니다.

**백엔드 LangGraph 노드 추가**
```
[check_progress]   완료율, 지연 할 일 분석
       │
[suggest_adjust]   Claude API — 재조정 제안 생성 (변경 이유 포함)
       │
 API 응답 (제안 목록 + 이유 설명)
```

**프론트엔드**
- 대시보드 "에이전트 브리핑" 카드에 AI 제안 내용 표시
- 제안 수락 / 거절 버튼

---

### 1-4. 재조정 알고리즘 — 평일/주말 용량 반영
현재 재조정은 `available_hours`를 무시하고 균등 분배만 합니다.  
DB에 `available_hours_weekday/weekend` 저장이 완료되었으므로 바로 활용 가능합니다.

**백엔드** ([reschedule.py](file:///Users/User/src/repos/Hierar-Do/backend/app/api/v1/reschedule.py))
- 평일/주말별 하루 용량(분) 계산
- `estimated_minutes`를 합산해 용량 초과 시 다음 날로 이월
- 결과: 더 현실적인 일정 재배치

---

### 1-5. 프론트엔드 테스트 추가
현재 프론트엔드 테스트가 전혀 없습니다.

- Vitest + React Testing Library 설정
- 핵심 컴포넌트 테스트: `GoalModal`, `MonthCalendar`, `WeekDetail`
- 커스텀 훅 테스트: `useToggleTodo`, `useCreateGoal`

---

## Phase 2 — 사용자 인증 & 멀티유저
> *현재 `user_id=1` 하드코딩 → 실제 서비스 전환*

### 2-1. JWT 인증 도입

**백엔드 신규 API**
- `POST /api/v1/auth/register` — 이메일/비밀번호 회원가입
- `POST /api/v1/auth/login` — JWT 액세스 토큰 발급
- `GET /api/v1/auth/me` — 현재 사용자 정보 조회
- 모든 보호된 엔드포인트에 `current_user: User = Depends(get_current_user)` 의존성 주입
- [constants.py](file:///Users/User/src/repos/Hierar-Do/backend/app/constants.py)의 `MVP_USER_ID` 완전 제거

**추가 패키지**
```toml
python-jose = "^3.3.0"   # JWT 서명/검증
passlib = "^1.7.4"       # 비밀번호 해싱
bcrypt = "^4.0.0"        # bcrypt 해싱 백엔드
```

**프론트엔드**
- 로그인 / 회원가입 페이지 (`/login`, `/register`)
- JWT 토큰 저장 (HttpOnly 쿠키 권장)
- `useAuth` 훅 + Context Provider
- 미인증 시 `/login`으로 리다이렉트 (Next.js Middleware 활용)

---

### 2-2. Google 소셜 로그인
- Google OAuth 2.0 (현재 `google-auth` 패키지가 이미 설치되어 있어 진입 장벽 낮음)
- 로그인 페이지에 "Google로 계속하기" 버튼 추가

---

## Phase 3 — AI 기능 고도화
> *LangGraph를 더 활용한 스마트한 경험*

### 3-1. pgvector 기반 과거 패턴 개인화
현재 pgvector 확장만 설치되어 있고 실제로 사용되지 않습니다.

**설계**
- 목표 완료 시 `GoalEmbedding` 저장 (목표 텍스트 임베딩 + 결과)
- 새 목표 생성 시 유사한 과거 목표 검색 (코사인 유사도)
- `decompose_node`에 과거 패턴을 컨텍스트로 주입 → 더 정밀한 분해

```python
class GoalEmbedding(Base):
    __tablename__ = "goal_embeddings"
    id: Mapped[int]
    goal_id: Mapped[int]       # FK → Goal
    embedding: Mapped[Vector]  # pgvector (1536차원)
    outcome: Mapped[str]       # "completed" / "abandoned"
```

---

### 3-2. 진척도 기반 동적 재조정
단순 날짜 균등 분배가 아닌 실제 진척 패턴 분석.

**LangGraph 노드 추가**
```
[analyze_progress]   완료율, 예상 vs 실제 소요 시간 비교
        │
[smart_reschedule]   Claude API — 남은 기간과 패턴 고려한 재배치
                     "이 속도면 3주차가 위험해요" 식 코멘트 포함
```

---

### 3-3. 에이전트 브리핑 탭 구현
현재 대시보드 "에이전트 브리핑" 카드가 정적이고, 하단 네비 "브리핑" 탭은 준비 중 토스트만 표시합니다.

**백엔드**
- `GET /api/v1/briefing` — 오늘의 AI 브리핑 생성 (스트리밍)
  - 오늘 할 일 요약, 마감 임박 경고, 동기부여 메시지

**프론트엔드**
- 브리핑 페이지 (`/briefing`) 구현
- Server-Sent Events로 스트리밍 텍스트 효과

---

### 3-4. 할 일 실제 소요 시간 기록
`estimated_minutes`가 현재 AI 추정 고정값으로만 남아있습니다.

- Todo 완료 시 실제 소요 시간 선택적 입력 (`actual_minutes` 컬럼 추가)
- 다음 유사 할 일 생성 시 실제 데이터로 `estimated_minutes` 자동 보정

---

## Phase 4 — 에코시스템 확장
> *외부 서비스 연동 & 플랫폼화*

### 4-1. Google Calendar 연동
- `GET /api/v1/calendar/sync` — Google Calendar 일정 조회 → `available_hours` 자동 계산
- Todo를 Google Calendar 이벤트로 내보내기 (`PUSH /api/v1/todos/{id}/export`)

### 4-2. 알림 시스템
- 매일 아침 오늘 할 일 이메일 알림 (Celery + Redis 또는 APScheduler)
- 마감 D-3 경고 알림
- 주간 완료율 리포트

### 4-3. PWA 전환
- Next.js에 `next-pwa` 추가 → `manifest.json` + Service Worker
- 홈 화면 추가 설치 가능
- 네이티브 Web Push 알림 지원

### 4-4. 팀 목표 관리
- `Team`, `TeamMember` 모델 추가
- 팀 목표 공유 및 담당자(assignee) 지정
- 팀원 진척률 대시보드

---

## 우선순위 한눈에 보기

| 우선순위 | 항목 | 난이도 | 임팩트 |
|---------|------|--------|--------|
| 🔥 즉시 | **1-1** 목표/할 일 수동 편집 | 중 | 🔴 필수 |
| 🔥 즉시 | **1-2** 목표 완료 & 진척률 시각화 | 중 | 🔴 필수 |
| 🔥 즉시 | **1-3** AI 재조정 제안 (suggest/apply) | 중 | 🔴 설계에 이미 있음 |
| ⚡ 단기 | **1-4** 재조정 평일/주말 용량 반영 | 소 | 🟠 데이터 이미 있음 |
| ⚡ 단기 | **1-5** 프론트엔드 테스트 | 중 | 🟠 품질 |
| 🚀 중기 | **2-1** JWT 인증 | 대 | 🔴 멀티유저 전제 |
| 🚀 중기 | **2-2** Google 소셜 로그인 | 중 | 🟠 UX |
| 🌟 장기 | **3-1** pgvector 개인화 | 대 | 🟡 차별화 |
| 🌟 장기 | **3-3** 에이전트 브리핑 탭 | 중 | 🟡 UX |
| 🌟 장기 | **4-1** Google Calendar 연동 | 대 | 🟡 편의 |
| 🌟 장기 | **4-2** 알림 시스템 | 중 | 🟡 리텐션 |
| 🌟 장기 | **4-3** PWA 전환 | 소 | 🟡 접근성 |

---

## 기술 부채 (언제든 처리)

| 항목 | 위치 | 설명 |
|------|------|------|
| GoalStatus 이중 Enum | [schemas/goal.py](file:///Users/User/src/repos/Hierar-Do/backend/app/schemas/goal.py) | models와 schemas에 동일한 Enum 중복 정의 |
| Milestone.status 미사용 | [milestone.py](file:///Users/User/src/repos/Hierar-Do/backend/app/models/milestone.py) | status 컬럼이 항상 `pending`으로 방치됨 |
| 재조정 undo 없음 | [reschedule.py](file:///Users/User/src/repos/Hierar-Do/backend/app/api/v1/reschedule.py) | 재조정 후 되돌리기 불가 |
| LLM 타임아웃/재시도 없음 | [goals.py](file:///Users/User/src/repos/Hierar-Do/backend/app/api/v1/goals.py) | API 호출 실패 시 재시도 로직 없음 |
| React Error Boundary 없음 | frontend | 컴포넌트 에러 시 전체 앱 크래시 가능 |
| 에러 모니터링 없음 | — | Sentry 등 에러 추적 도구 미설정 |
