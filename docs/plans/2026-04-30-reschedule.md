# Reschedule Feature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 캘린더 페이지에 "일정 재조정" 버튼을 추가해 모든 목표의 미완료 todo를 오늘~deadline 사이에 재분배하고, 사용자가 미리보기 모달에서 승인 후 적용한다.

**Architecture:** 백엔드에 `POST /api/v1/reschedule/preview`(DB 변경 없음)와 `POST /api/v1/reschedule/apply`(DB 반영) 엔드포인트를 추가한다. 프론트엔드는 TanStack Query mutation 두 개와 `RescheduleModal` 컴포넌트로 미리보기→승인 플로우를 구현한다. 재조정 알고리즘은 기존 `schedule_node`와 동일한 균등분배 로직(LLM 없음)을 재사용한다.

**Tech Stack:** FastAPI, SQLAlchemy async, Pydantic v2, pytest-asyncio, Next.js 16 App Router, TanStack Query v5, TypeScript, Tailwind CSS.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `backend/app/api/v1/reschedule.py` | 재조정 알고리즘 + preview/apply 엔드포인트 |
| Create | `backend/tests/test_reschedule_api.py` | 엔드포인트 TDD 테스트 |
| Modify | `backend/app/main.py` | reschedule 라우터 등록 |
| Modify | `frontend/src/lib/types.ts` | `RescheduleItem` 인터페이스 추가 |
| Modify | `frontend/src/lib/api.ts` | `post` body를 optional로 변경 |
| Modify | `frontend/src/lib/queries.ts` | `useReschedulePreview`, `useRescheduleApply` 훅 추가 |
| Create | `frontend/src/components/RescheduleModal.tsx` | 미리보기 모달 컴포넌트 |
| Modify | `frontend/src/app/calendar/page.tsx` | 버튼 + 모달 상태 연결 |

---

### Task 1: Backend reschedule module (TDD)

**Files:**
- Create: `backend/app/api/v1/reschedule.py`
- Create: `backend/tests/test_reschedule_api.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_reschedule_api.py
import pytest


@pytest.mark.asyncio
async def test_preview_empty_when_no_goals(client):
    resp = await client.post("/api/v1/reschedule/preview")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_apply_empty_when_no_goals(client):
    resp = await client.post("/api/v1/reschedule/apply")
    assert resp.status_code == 200
    assert resp.json() == {"updated": 0}


@pytest.mark.asyncio
async def test_preview_empty_when_all_todos_done(client, mock_pipeline):
    create_resp = await client.post(
        "/api/v1/goals",
        json={"raw_input": "테스트", "available_hours": {"weekday": 2, "weekend": 4}},
    )
    todos = create_resp.json()["todos"]
    for todo in todos:
        await client.patch(f"/api/v1/todos/{todo['id']}/done")

    resp = await client.post("/api/v1/reschedule/preview")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_preview_returns_rescheduled_items(client, mock_pipeline):
    # mock creates 12 todos (4 milestones × 3 todos) all with due_date=deadline(today+28)
    # algorithm redistributes from today → 8 of 12 get new dates
    await client.post(
        "/api/v1/goals",
        json={"raw_input": "테스트", "available_hours": {"weekday": 2, "weekend": 4}},
    )
    resp = await client.post("/api/v1/reschedule/preview")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) > 0
    for item in items:
        assert item["old_due_date"] != item["new_due_date"]
        assert "todo_id" in item
        assert "title" in item
        assert "new_due_date" in item


@pytest.mark.asyncio
async def test_apply_updates_todo_due_dates(client, mock_pipeline):
    await client.post(
        "/api/v1/goals",
        json={"raw_input": "테스트", "available_hours": {"weekday": 2, "weekend": 4}},
    )
    preview_items = (await client.post("/api/v1/reschedule/preview")).json()
    assert len(preview_items) > 0

    resp = await client.post("/api/v1/reschedule/apply")
    assert resp.status_code == 200
    assert resp.json()["updated"] == len(preview_items)


@pytest.mark.asyncio
async def test_apply_is_idempotent(client, mock_pipeline):
    await client.post(
        "/api/v1/goals",
        json={"raw_input": "테스트", "available_hours": {"weekday": 2, "weekend": 4}},
    )
    first = await client.post("/api/v1/reschedule/apply")
    assert first.json()["updated"] > 0

    second = await client.post("/api/v1/reschedule/apply")
    assert second.json()["updated"] == 0
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd backend
poetry run pytest tests/test_reschedule_api.py -v
```

Expected: 6 failures — `404 Not Found` (router not registered yet)

- [ ] **Step 3: Create `reschedule.py`**

```python
# backend/app/api/v1/reschedule.py
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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
        todos = [t for m in goal.milestones for t in m.todos if not t.is_done]
        if not todos:
            continue
        remaining = max((goal.deadline - today).days, 0)
        n = len(todos)
        for i, todo in enumerate(todos):
            if remaining == 0 or n == 1:
                new_date = today
            else:
                offset = int(i * remaining / (n - 1))
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

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd backend
poetry run pytest tests/test_reschedule_api.py -v
```

Expected: 6 passed (router not yet registered in main.py — tests still fail with 404)

> **Note:** If tests still show 404, proceed to Task 2 first (register router), then re-run.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/reschedule.py backend/tests/test_reschedule_api.py
git commit -m "feat: add reschedule preview and apply endpoints (TDD)"
```

---

### Task 2: Register reschedule router in main.py

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Add import and router registration**

Current `backend/app/main.py`:
```python
from app.api.v1 import goals as goals_router
from app.api.v1 import todos as todos_router
# ...
app.include_router(goals_router.router, prefix="/api/v1")
app.include_router(todos_router.router, prefix="/api/v1")
```

Replace with:
```python
from app.api.v1 import goals as goals_router
from app.api.v1 import todos as todos_router
from app.api.v1 import reschedule as reschedule_router
# ...
app.include_router(goals_router.router, prefix="/api/v1")
app.include_router(todos_router.router, prefix="/api/v1")
app.include_router(reschedule_router.router, prefix="/api/v1")
```

- [ ] **Step 2: Run all tests**

```bash
cd backend
poetry run pytest -v
```

Expected: all tests pass including the 6 new reschedule tests

- [ ] **Step 3: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: register reschedule router"
```

---

### Task 3: Frontend types, api helper, and hooks

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/lib/queries.ts`

- [ ] **Step 1: Add `RescheduleItem` to `types.ts`**

Append to the end of `frontend/src/lib/types.ts`:

```ts
export interface RescheduleItem {
  todo_id: number;
  title: string;
  old_due_date: string | null;
  new_due_date: string;
}
```

- [ ] **Step 2: Make `api.post` body optional in `api.ts`**

Current `frontend/src/lib/api.ts`:
```ts
post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
```

Replace with:
```ts
post: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "POST",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),
```

- [ ] **Step 3: Add hooks to `queries.ts`**

First, update the existing import line at the top of `frontend/src/lib/queries.ts`:

```ts
// 기존
import type { CreateGoalRequest, CreateGoalResponse, Goal } from "@/lib/types";
// 변경
import type { CreateGoalRequest, CreateGoalResponse, Goal, RescheduleItem } from "@/lib/types";
```

Then append the two new hooks at the end of the file:

```ts
export function useReschedulePreview() {
  return useMutation<RescheduleItem[], Error, void>({
    mutationFn: () => api.post<RescheduleItem[]>("/api/v1/reschedule/preview"),
  });
}

export function useRescheduleApply() {
  const queryClient = useQueryClient();
  return useMutation<{ updated: number }, Error, void>({
    mutationFn: () => api.post<{ updated: number }>("/api/v1/reschedule/apply"),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["goals"] }),
  });
}
```

- [ ] **Step 4: Verify TypeScript**

```bash
cd frontend
npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts frontend/src/lib/queries.ts
git commit -m "feat: add RescheduleItem type, optional post body, reschedule hooks"
```

---

### Task 4: RescheduleModal component

**Files:**
- Create: `frontend/src/components/RescheduleModal.tsx`

- [ ] **Step 1: Create the file**

```tsx
// frontend/src/components/RescheduleModal.tsx
"use client";
import { useEffect, useRef } from "react";
import type { RescheduleItem } from "@/lib/types";

interface RescheduleModalProps {
  items: RescheduleItem[];
  onApply: () => void;
  onClose: () => void;
  isApplying: boolean;
}

const TODAY_STR = new Date().toISOString().slice(0, 10);

export function RescheduleModal({
  items,
  onApply,
  onClose,
  isApplying,
}: RescheduleModalProps) {
  const backdropRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  function handleBackdropClick(e: React.MouseEvent) {
    if (e.target === backdropRef.current) onClose();
  }

  return (
    <div
      ref={backdropRef}
      onClick={handleBackdropClick}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
    >
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 flex flex-col gap-5 max-h-[80vh]">
        <div>
          <h2 className="text-xl font-extrabold text-primary">일정 재조정 미리보기</h2>
          <p className="text-sm text-on-surface-variant mt-1">
            {items.length}개 항목이 변경됩니다.
          </p>
        </div>

        <div className="overflow-y-auto flex-1 flex flex-col gap-2">
          {items.map((item) => {
            const isOverdue =
              item.old_due_date !== null && item.old_due_date < TODAY_STR;
            return (
              <div
                key={item.todo_id}
                className={`flex items-start gap-3 p-3 rounded-lg border ${
                  isOverdue
                    ? "border-red-200 bg-red-50"
                    : "border-outline-variant bg-surface"
                }`}
              >
                <div className="flex-1 min-w-0">
                  <p
                    className={`text-sm font-semibold truncate ${
                      isOverdue ? "text-red-600" : "text-on-surface"
                    }`}
                  >
                    {item.title}
                  </p>
                  <p className="text-xs text-outline mt-0.5">
                    {item.old_due_date ?? "날짜 없음"} → {item.new_due_date}
                  </p>
                </div>
              </div>
            );
          })}
        </div>

        <div className="flex gap-3">
          <button
            onClick={onClose}
            disabled={isApplying}
            className="flex-1 py-3 rounded-xl border border-outline-variant text-on-surface font-bold text-sm disabled:opacity-50 hover:bg-surface transition-colors"
          >
            취소
          </button>
          <button
            onClick={onApply}
            disabled={isApplying}
            className="flex-1 py-3 rounded-xl bg-primary text-white font-bold text-sm disabled:opacity-50 hover:bg-primary/90 transition-colors"
          >
            {isApplying ? "적용 중..." : "적용"}
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd frontend
npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/RescheduleModal.tsx
git commit -m "feat: add RescheduleModal component"
```

---

### Task 5: Wire button and modal into calendar page

**Files:**
- Modify: `frontend/src/app/calendar/page.tsx`

- [ ] **Step 1: Replace the entire file**

```tsx
// frontend/src/app/calendar/page.tsx
"use client";
import Link from "next/link";
import { useMemo, useState } from "react";
import { useGoals, useToggleTodo, useReschedulePreview, useRescheduleApply } from "@/lib/queries";
import { MonthCalendar } from "@/components/MonthCalendar";
import { WeekDetail } from "@/components/WeekDetail";
import { RescheduleModal } from "@/components/RescheduleModal";
import type { RescheduleItem, Todo } from "@/lib/types";

export default function CalendarPage() {
  const [selectedDate, setSelectedDate] = useState<string>(() => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  });
  const [rescheduleItems, setRescheduleItems] = useState<RescheduleItem[] | null>(null);
  const [noChanges, setNoChanges] = useState(false);

  const { data: goals = [], isLoading } = useGoals();
  const { mutate: toggleTodo } = useToggleTodo();
  const { mutate: previewReschedule, isPending: isPreviewing } = useReschedulePreview();
  const { mutate: applyReschedule, isPending: isApplying } = useRescheduleApply();

  const todosByDate = useMemo<Record<string, Todo[]>>(() => {
    const map: Record<string, Todo[]> = {};
    goals
      .flatMap((g) => g.milestones.flatMap((m) => m.todos))
      .filter((t): t is Todo & { due_date: string } => t.due_date !== null)
      .forEach((t) => {
        map[t.due_date] ??= [];
        map[t.due_date].push(t);
      });
    return map;
  }, [goals]);

  function handleRescheduleClick() {
    previewReschedule(undefined, {
      onSuccess: (items) => {
        if (items.length === 0) {
          setNoChanges(true);
          setTimeout(() => setNoChanges(false), 3000);
        } else {
          setRescheduleItems(items);
        }
      },
    });
  }

  function handleApply() {
    applyReschedule(undefined, {
      onSuccess: () => setRescheduleItems(null),
    });
  }

  return (
    <>
      <header className="fixed top-0 left-0 w-full z-50 flex items-center px-4 h-16 bg-slate-50 border-b border-slate-200">
        <Link
          href="/"
          className="flex items-center gap-1 text-primary hover:opacity-80 transition-opacity"
        >
          <span className="material-symbols-outlined">arrow_back</span>
          <span className="text-sm font-bold">돌아가기</span>
        </Link>
        <h1 className="flex-1 text-center text-lg font-extrabold tracking-tight text-primary">
          캘린더
        </h1>
        <div className="flex flex-col items-end w-16">
          <button
            onClick={handleRescheduleClick}
            disabled={isPreviewing}
            className="text-xs font-bold text-primary hover:opacity-70 transition-opacity disabled:opacity-40"
          >
            {isPreviewing ? "..." : "재조정"}
          </button>
          {noChanges && (
            <span className="text-[10px] text-outline whitespace-nowrap">
              재조정할 일정이 없어요.
            </span>
          )}
        </div>
      </header>

      <main className="pt-24 pb-24 px-4 max-w-[1400px] mx-auto">
        {isLoading ? (
          <div className="pt-16 text-center text-on-surface-variant text-sm">
            로딩 중...
          </div>
        ) : (
          <>
            <MonthCalendar
              todosByDate={todosByDate}
              selectedDate={selectedDate}
              onDateSelect={setSelectedDate}
            />
            <WeekDetail
              selectedDate={selectedDate}
              todosByDate={todosByDate}
              onToggle={(todoId, isDone) => toggleTodo({ todoId, isDone })}
            />
          </>
        )}
      </main>

      {rescheduleItems && (
        <RescheduleModal
          items={rescheduleItems}
          onApply={handleApply}
          onClose={() => setRescheduleItems(null)}
          isApplying={isApplying}
        />
      )}
    </>
  );
}
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd frontend
npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 3: Verify build**

```bash
cd frontend
npm run build 2>&1 | tail -10
```

Expected: `✓ Compiled successfully`

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/calendar/page.tsx
git commit -m "feat: wire reschedule button and modal into calendar page"
```
