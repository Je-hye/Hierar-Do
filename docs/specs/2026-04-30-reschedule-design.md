# Reschedule Feature — Design Spec
**Date:** 2026-04-30
**Status:** Approved

---

## Overview

캘린더 페이지에서 "일정 재조정" 버튼을 누르면 AI(순수 Python)가 모든 목표의 미완료 todo를 오늘~deadline 사이에 재분배한다. 미리보기 모달로 변경 전/후를 확인한 뒤 사용자가 적용을 승인한다.

---

## Scope

**변경 대상:**
- `backend/app/api/v1/reschedule.py` — 신규: preview/apply 엔드포인트
- `backend/app/main.py` — reschedule 라우터 등록
- `frontend/src/lib/queries.ts` — `useReschedulePreview`, `useRescheduleApply` 훅 추가
- `frontend/src/app/calendar/page.tsx` — 헤더 버튼 + 모달 상태
- `frontend/src/components/RescheduleModal.tsx` — 신규: 미리보기 모달

---

## User Flow

1. 사용자가 캘린더 페이지 헤더에서 "일정 재조정" 버튼 클릭
2. `POST /api/v1/reschedule/preview` 호출 → 로딩 스피너 표시
3. 응답 수신 → `RescheduleModal` 열림 (변경 항목 목록 표시)
4. 변경이 없으면 모달 대신 버튼 근처에 "재조정할 일정이 없어요." 문구를 3초간 표시
5. 사용자가 "적용" 클릭 → `POST /api/v1/reschedule/apply` 호출
6. 성공 시 `["goals"]` 캐시 무효화 → 캘린더 자동 갱신, 모달 닫힘
7. 사용자가 "취소" 클릭 → 모달 닫힘, DB 변경 없음

---

## Backend

### Reschedule Algorithm

각 목표에 대해:
1. 해당 목표의 미완료(`is_done=False`) todo 전체를 수집
2. `remaining_days = (goal.deadline - today).days`
3. `remaining_days <= 0`이면 모든 todo를 `today`로 설정
4. `remaining_days > 0`이면 기존 `schedule_node`와 동일한 균등 분배 로직 적용:
   - todo `i`의 새 due_date = `today + timedelta(days=int(i * remaining_days / max(n-1, 1)))`
   - 계산된 날짜가 `deadline`을 초과하면 `deadline`으로 클램프

이미 완료된 todo(`is_done=True`)는 변경하지 않는다.

### Endpoints

#### `POST /api/v1/reschedule/preview`

DB를 변경하지 않고 계산 결과만 반환한다.

**Response:** `list[RescheduleItem]`

```python
class RescheduleItem(BaseModel):
    todo_id: int
    title: str
    old_due_date: date | None
    new_due_date: date
```

변경이 없는 항목(old_due_date == new_due_date)은 응답에 포함하지 않는다.

#### `POST /api/v1/reschedule/apply`

위와 동일한 알고리즘을 실행하고 DB에 적용한다. 멱등성 보장을 위해 preview 결과를 클라이언트가 전달하지 않고 서버가 재계산한다.

**Response:** `{ "updated": int }` — 변경된 todo 수

### New File: `backend/app/api/v1/reschedule.py`

```python
from datetime import date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from app.db.session import get_db
from app.models.goal import Goal
from app.models.milestone import Milestone
from app.models.todo import Todo

router = APIRouter(prefix="/reschedule", tags=["reschedule"])
_MVP_USER_ID = 1


class RescheduleItem(BaseModel):
    todo_id: int
    title: str
    old_due_date: date | None
    new_due_date: date


def _compute_reschedule(goals: list[Goal]) -> list[tuple[Todo, date]]:
    today = date.today()
    result: list[tuple[Todo, date]] = []
    for goal in goals:
        todos = [
            t
            for m in goal.milestones
            for t in m.todos
            if not t.is_done
        ]
        if not todos:
            continue
        remaining = max((goal.deadline - today).days, 0)
        n = len(todos)
        for i, todo in enumerate(todos):
            if remaining == 0:
                new_date = today
            else:
                offset = int(i * remaining / max(n - 1, 1)) if n > 1 else 0
                new_date = today + timedelta(days=offset)
                if new_date > goal.deadline:
                    new_date = goal.deadline
            result.append((todo, new_date))
    return result


async def _load_goals(db: AsyncSession) -> list[Goal]:
    rows = await db.execute(
        select(Goal)
        .where(Goal.user_id == _MVP_USER_ID)
        .options(selectinload(Goal.milestones).selectinload(Milestone.todos))
    )
    return list(rows.scalars().all())


@router.post("/preview", response_model=list[RescheduleItem])
async def preview_reschedule(db: AsyncSession = Depends(get_db)):
    goals = await _load_goals(db)
    changes = _compute_reschedule(goals)
    return [
        RescheduleItem(
            todo_id=todo.id,
            title=todo.title,
            old_due_date=todo.due_date,
            new_due_date=new_date,
        )
        for todo, new_date in changes
        if todo.due_date != new_date
    ]


@router.post("/apply", response_model=dict)
async def apply_reschedule(db: AsyncSession = Depends(get_db)):
    goals = await _load_goals(db)
    changes = _compute_reschedule(goals)
    count = 0
    for todo, new_date in changes:
        if todo.due_date != new_date:
            todo.due_date = new_date
            count += 1
    if count:
        await db.commit()
    return {"updated": count}
```

### `backend/app/main.py` 수정

`reschedule` 라우터를 `v1` 라우터에 등록한다.

---

## Frontend

### New Types (in `frontend/src/lib/types.ts`)

```ts
export interface RescheduleItem {
  todo_id: number;
  title: string;
  old_due_date: string | null;
  new_due_date: string;
}
```

### New Hooks (in `frontend/src/lib/queries.ts`)

```ts
export function useReschedulePreview() {
  return useMutation<RescheduleItem[], Error>({
    mutationFn: () => api.post<RescheduleItem[]>("/api/v1/reschedule/preview"),
  });
}

export function useRescheduleApply() {
  const queryClient = useQueryClient();
  return useMutation<{ updated: number }, Error>({
    mutationFn: () => api.post<{ updated: number }>("/api/v1/reschedule/apply"),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["goals"] }),
  });
}
```

### New Component: `frontend/src/components/RescheduleModal.tsx`

- Props: `items: RescheduleItem[]`, `onApply: () => void`, `onClose: () => void`, `isApplying: boolean`
- 헤더: "일정 재조정 미리보기"
- 내용: 각 항목을 `{title}: {old_due_date} → {new_due_date}` 형태로 표시
  - `old_due_date`가 오늘보다 이전이면 해당 행을 `text-red-500`으로 강조
- 하단: "취소" 버튼 + "적용" 버튼 (isApplying 중에는 비활성화)
- ESC 키 / 백드롭 클릭으로 닫기

### `frontend/src/app/calendar/page.tsx` 수정

헤더 우측 `<div className="w-16" />`을 "일정 재조정" 버튼으로 교체:

```tsx
<button onClick={handleRescheduleClick} disabled={isPreviewing} className="...">
  {isPreviewing ? "..." : "재조정"}
</button>
```

상태:
- `rescheduleItems: RescheduleItem[] | null` — null이면 모달 닫힘
- `useReschedulePreview` mutation의 `isPending`으로 로딩 표시
- preview 결과가 빈 배열이면 모달 없이 버튼 근처에 "재조정할 일정이 없어요." 문구를 3초간 표시 (`setTimeout`으로 상태 초기화)

---

## MVP 제외

- 재조정 히스토리 / 실행취소(undo)
- 특정 todo만 선택해서 재조정
- 재조정 주기 자동화 (매일 자정 크론)
