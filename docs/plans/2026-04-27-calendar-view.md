# Calendar View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** AI가 생성한 할 일을 월간 캘린더로 보여주고, 날짜 클릭 시 해당 주의 상세 일정을 표시한다.

**Architecture:** `useGoals()`로 받아온 todos를 `due_date` 기준으로 `Record<string, Todo[]>` 맵으로 변환해 `MonthCalendar`와 `WeekDetail` 컴포넌트에 전달한다. `/calendar` 페이지가 상태(`selectedDate`)를 소유하고 두 컴포넌트를 조합한다.

**Tech Stack:** Next.js 16.2.4 App Router, TanStack Query v5, TypeScript, Tailwind CSS.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `frontend/src/components/MonthCalendar.tsx` | 월간 그리드, 날짜 선택 |
| Create | `frontend/src/components/WeekDetail.tsx` | 주간 드릴다운 패널 |
| Replace | `frontend/src/app/calendar/page.tsx` | 실제 데이터 연결, 두 컴포넌트 조합 |
| Modify | `frontend/src/app/page.tsx` | 메뉴 아이콘 → `/calendar` 링크 |

---

### Task 1: Create MonthCalendar component

**Files:**
- Create: `frontend/src/components/MonthCalendar.tsx`

- [ ] **Step 1: Create the file**

```tsx
// frontend/src/components/MonthCalendar.tsx
"use client";
import { useState } from "react";
import type { Todo } from "@/lib/types";

interface MonthCalendarProps {
  todosByDate: Record<string, Todo[]>;
  selectedDate: string | null;
  onDateSelect: (date: string) => void;
}

function toDateStr(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function getCalendarDays(year: number, month: number): (Date | null)[] {
  const firstDay = new Date(year, month, 1);
  const lastDay = new Date(year, month + 1, 0);
  const startPad = firstDay.getDay(); // 0=일요일
  const days: (Date | null)[] = [];
  for (let i = 0; i < startPad; i++) days.push(null);
  for (let d = 1; d <= lastDay.getDate(); d++) {
    days.push(new Date(year, month, d));
  }
  return days;
}

export function MonthCalendar({ todosByDate, selectedDate, onDateSelect }: MonthCalendarProps) {
  const today = new Date();
  const [currentMonth, setCurrentMonth] = useState(
    new Date(today.getFullYear(), today.getMonth(), 1)
  );

  const year = currentMonth.getFullYear();
  const month = currentMonth.getMonth();
  const days = getCalendarDays(year, month);
  const todayStr = toDateStr(today);

  return (
    <div className="bg-white border border-outline-variant rounded-xl shadow-sm p-4">
      <div className="flex justify-between items-center mb-4">
        <button
          onClick={() => setCurrentMonth(new Date(year, month - 1, 1))}
          className="p-1 hover:bg-surface rounded-lg transition-colors"
        >
          <span className="material-symbols-outlined text-outline">chevron_left</span>
        </button>
        <span className="font-bold text-lg text-on-surface">
          {year}년 {month + 1}월
        </span>
        <button
          onClick={() => setCurrentMonth(new Date(year, month + 1, 1))}
          className="p-1 hover:bg-surface rounded-lg transition-colors"
        >
          <span className="material-symbols-outlined text-outline">chevron_right</span>
        </button>
      </div>

      <div className="grid grid-cols-7 gap-1 text-center mb-2">
        {["일", "월", "화", "수", "목", "금", "토"].map((d) => (
          <span key={d} className="text-xs font-bold text-outline">
            {d}
          </span>
        ))}
      </div>

      <div className="grid grid-cols-7 gap-1 text-center">
        {days.map((date, i) => {
          if (!date) return <div key={`empty-${i}`} />;
          const dateStr = toDateStr(date);
          const isToday = dateStr === todayStr;
          const isSelected = dateStr === selectedDate;
          const hasTodos = !!todosByDate[dateStr]?.length;

          return (
            <button
              key={dateStr}
              onClick={() => onDateSelect(dateStr)}
              className={`flex flex-col items-center py-1.5 rounded-lg transition-colors ${
                isSelected
                  ? "bg-primary text-white"
                  : isToday
                  ? "border border-primary text-primary"
                  : "hover:bg-surface text-on-surface"
              }`}
            >
              <span className="text-sm font-medium">{date.getDate()}</span>
              {hasTodos && (
                <span
                  className={`w-1 h-1 rounded-full mt-0.5 ${
                    isSelected ? "bg-white" : "bg-primary"
                  }`}
                />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend
npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/MonthCalendar.tsx
git commit -m "feat: add MonthCalendar component"
```

---

### Task 2: Create WeekDetail component

**Files:**
- Create: `frontend/src/components/WeekDetail.tsx`

- [ ] **Step 1: Create the file**

```tsx
// frontend/src/components/WeekDetail.tsx
"use client";
import type { Todo } from "@/lib/types";

interface WeekDetailProps {
  selectedDate: string;
  todosByDate: Record<string, Todo[]>;
  onToggle: (todoId: number, isDone: boolean) => void;
}

const DAY_LABELS = ["월", "화", "수", "목", "금", "토", "일"];

function toDateStr(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function getWeekDays(dateStr: string): Date[] {
  const date = new Date(dateStr);
  const day = date.getDay(); // 0=일요일
  const diffToMonday = day === 0 ? -6 : 1 - day;
  const monday = new Date(date);
  monday.setDate(date.getDate() + diffToMonday);
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(monday);
    d.setDate(monday.getDate() + i);
    return d;
  });
}

export function WeekDetail({ selectedDate, todosByDate, onToggle }: WeekDetailProps) {
  const weekDays = getWeekDays(selectedDate);
  const hasAnyTodo = weekDays.some((d) => todosByDate[toDateStr(d)]?.length);
  const firstDay = weekDays[0];
  const lastDay = weekDays[6];

  return (
    <div className="mt-6">
      <h3 className="font-bold text-lg text-on-surface mb-4">
        {firstDay.getMonth() + 1}월 {firstDay.getDate()}일 —{" "}
        {lastDay.getMonth() + 1}월 {lastDay.getDate()}일
      </h3>
      {!hasAnyTodo ? (
        <div className="text-sm text-on-surface-variant text-center py-8">
          이 주에는 할 일이 없어요.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <div className="grid grid-cols-7 gap-3 min-w-[700px]">
            {weekDays.map((day, i) => {
              const dateStr = toDateStr(day);
              const isSelected = dateStr === selectedDate;
              const todos = todosByDate[dateStr] ?? [];
              return (
                <div key={dateStr}>
                  <div
                    className={`text-center mb-2 py-1 rounded-lg ${
                      isSelected ? "bg-primary text-white" : ""
                    }`}
                  >
                    <div className="text-[10px] font-bold">{DAY_LABELS[i]}</div>
                    <div className="text-sm font-bold">{day.getDate()}</div>
                  </div>
                  <div className="flex flex-col gap-2">
                    {todos.map((todo) => (
                      <label
                        key={todo.id}
                        className="flex items-start gap-2 p-2 bg-white border border-outline-variant rounded-lg cursor-pointer hover:bg-surface transition-colors"
                      >
                        <input
                          type="checkbox"
                          checked={todo.is_done}
                          onChange={() => onToggle(todo.id, !todo.is_done)}
                          className="mt-0.5 w-4 h-4 rounded border-outline text-primary focus:ring-primary shrink-0"
                        />
                        <div className="flex-1 min-w-0">
                          <span
                            className={`text-xs font-semibold block truncate ${
                              todo.is_done
                                ? "line-through text-outline"
                                : "text-on-surface"
                            }`}
                          >
                            {todo.title}
                          </span>
                          {todo.estimated_minutes > 0 && (
                            <span className="text-[10px] text-outline">
                              {todo.estimated_minutes}분
                            </span>
                          )}
                        </div>
                      </label>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend
npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/WeekDetail.tsx
git commit -m "feat: add WeekDetail component for weekly drill-down"
```

---

### Task 3: Replace calendar/page.tsx with real data

**Files:**
- Replace: `frontend/src/app/calendar/page.tsx`

- [ ] **Step 1: Replace the entire file**

```tsx
// frontend/src/app/calendar/page.tsx
"use client";
import Link from "next/link";
import { useState } from "react";
import { useGoals, useToggleTodo } from "@/lib/queries";
import { MonthCalendar } from "@/components/MonthCalendar";
import { WeekDetail } from "@/components/WeekDetail";
import type { Todo } from "@/lib/types";

export default function CalendarPage() {
  const today = new Date();
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;

  const [selectedDate, setSelectedDate] = useState<string>(todayStr);
  const { data: goals = [], isLoading } = useGoals();
  const { mutate: toggleTodo } = useToggleTodo();

  const todosByDate: Record<string, Todo[]> = {};
  goals
    .flatMap((g) => g.milestones.flatMap((m) => m.todos))
    .filter((t): t is Todo & { due_date: string } => t.due_date !== null)
    .forEach((t) => {
      todosByDate[t.due_date] ??= [];
      todosByDate[t.due_date].push(t);
    });

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
        <div className="w-16" />
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
    </>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend
npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 3: Verify build**

```bash
cd frontend
npm run build 2>&1 | tail -15
```

Expected: `✓ Compiled successfully`

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/calendar/page.tsx
git commit -m "feat: replace calendar page with real data using MonthCalendar and WeekDetail"
```

---

### Task 4: Wire menu icon to /calendar in dashboard

**Files:**
- Modify: `frontend/src/app/page.tsx`

- [ ] **Step 1: Wrap the menu icon with a Link**

Find this block in `frontend/src/app/page.tsx`:

```tsx
        <div className="flex items-center gap-3">
          <span className="material-symbols-outlined text-primary">menu</span>
          <h1 className="text-xl font-extrabold tracking-tight text-primary">
            Hierar-Do
          </h1>
        </div>
```

Replace with:

```tsx
        <div className="flex items-center gap-3">
          <Link href="/calendar">
            <span className="material-symbols-outlined text-primary hover:opacity-70 transition-opacity">
              menu
            </span>
          </Link>
          <h1 className="text-xl font-extrabold tracking-tight text-primary">
            Hierar-Do
          </h1>
        </div>
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend
npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/page.tsx
git commit -m "feat: link menu icon to calendar page"
```
