# Frontend API Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace hardcoded dummy data in the dashboard with live backend API data, and add a FAB → modal flow for creating goals.

**Architecture:** TanStack Query v5 fetches from FastAPI backend (`http://localhost:8000`). A `QueryProvider` client component wraps the app in `layout.tsx`. The main dashboard becomes a client component using `useGoals` and `useToggleTodo` hooks, with `GoalModal` opening on FAB click.

**Tech Stack:** Next.js 16.2.4 (App Router), TanStack Query v5, TypeScript, Tailwind CSS, existing `src/lib/api.ts` fetch wrapper.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `frontend/src/lib/types.ts` | TypeScript types mirroring backend schemas |
| Create | `frontend/src/providers/QueryProvider.tsx` | `"use client"` wrapper for `QueryClientProvider` |
| Create | `frontend/src/lib/queries.ts` | TanStack Query hooks: `useGoals`, `useCreateGoal`, `useToggleTodo` |
| Create | `frontend/src/components/GoalModal.tsx` | FAB modal for goal creation |
| Modify | `frontend/src/app/layout.tsx` | Wrap `children` with `QueryProvider` |
| Modify | `frontend/src/app/page.tsx` | Replace hardcoded data with API hooks, add FAB |

---

### Task 1: Install TanStack Query

**Files:**
- Modify: `frontend/package.json` (via npm install)

- [ ] **Step 1: Install the package**

```bash
cd frontend
npm install @tanstack/react-query
```

- [ ] **Step 2: Verify installation**

```bash
ls node_modules/@tanstack/react-query/package.json
```

Expected: file exists (no error)

- [ ] **Step 3: Verify TypeScript types are bundled**

```bash
ls node_modules/@tanstack/react-query/build/legacy/index.d.ts
```

Expected: file exists

---

### Task 2: Create TypeScript types

**Files:**
- Create: `frontend/src/lib/types.ts`

- [ ] **Step 1: Create the file**

```ts
// frontend/src/lib/types.ts
export type GoalStatus = "pending" | "active" | "done";

export interface Todo {
  id: number;
  milestone_id: number;
  title: string;
  due_date: string | null;
  estimated_minutes: number;
  is_done: boolean;
  suggested_by_ai: boolean;
}

export interface Milestone {
  id: number;
  goal_id: number;
  title: string;
  week_number: number;
  status: string;
  suggested_by_ai: boolean;
  todos: Todo[];
}

export interface Goal {
  id: number;
  title: string;
  raw_input: string;
  deadline: string;
  status: GoalStatus;
  created_at: string;
  milestones: Milestone[];
}

export interface CreateGoalRequest {
  raw_input: string;
  available_hours: { weekday: number; weekend: number };
}

export interface CreateGoalResponse {
  goal: Goal;
  milestones: Milestone[];
  todos: Todo[];
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
cd frontend
git add src/lib/types.ts package.json package-lock.json
git commit -m "feat: add TypeScript types for backend API schema"
```

---

### Task 3: Create QueryProvider

**Files:**
- Create: `frontend/src/providers/QueryProvider.tsx`

`layout.tsx` is a server component and cannot use hooks directly. The pattern for Next.js App Router is to create a `"use client"` wrapper component.

- [ ] **Step 1: Create the provider**

```tsx
// frontend/src/providers/QueryProvider.tsx
"use client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { staleTime: 30_000 },
        },
      })
  );
  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend
npx tsc --noEmit
```

Expected: no errors

---

### Task 4: Update layout.tsx

**Files:**
- Modify: `frontend/src/app/layout.tsx`

- [ ] **Step 1: Replace layout.tsx**

```tsx
// frontend/src/app/layout.tsx
import type { Metadata } from "next";
import "./globals.css";
import { Geist } from "next/font/google";
import { cn } from "@/lib/utils";
import { QueryProvider } from "@/providers/QueryProvider";

const geist = Geist({ subsets: ["latin"], variable: "--font-sans" });

export const metadata: Metadata = {
  title: "Hierar-Do",
  description: "계층적 AI 할 일 관리",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" className={cn("light", "font-sans", geist.variable)}>
      <head>
        <link
          rel="stylesheet"
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css"
          crossOrigin="anonymous"
        />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap"
        />
      </head>
      <body className="bg-background text-on-surface font-sans antialiased">
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
cd frontend
npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add src/providers/QueryProvider.tsx src/app/layout.tsx
git commit -m "feat: add QueryProvider for TanStack Query"
```

---

### Task 5: Create query hooks

**Files:**
- Create: `frontend/src/lib/queries.ts`

- [ ] **Step 1: Create queries.ts**

```ts
// frontend/src/lib/queries.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { CreateGoalRequest, CreateGoalResponse, Goal } from "@/lib/types";

export function useGoals() {
  return useQuery<Goal[]>({
    queryKey: ["goals"],
    queryFn: () => api.get<Goal[]>("/api/v1/goals"),
    staleTime: 30_000,
  });
}

export function useCreateGoal(onSuccess?: () => void) {
  const queryClient = useQueryClient();
  return useMutation<CreateGoalResponse, Error, CreateGoalRequest>({
    mutationFn: (body) => api.post<CreateGoalResponse>("/api/v1/goals", body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["goals"] });
      onSuccess?.();
    },
  });
}

export function useToggleTodo() {
  const queryClient = useQueryClient();
  return useMutation<unknown, Error, { todoId: number; isDone: boolean }>({
    mutationFn: ({ todoId, isDone }) =>
      api.patch(`/api/v1/todos/${todoId}/${isDone ? "done" : "undone"}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["goals"] }),
  });
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
git add src/lib/queries.ts src/lib/types.ts
git commit -m "feat: add TanStack Query hooks for goals and todos"
```

---

### Task 6: Create GoalModal

**Files:**
- Create: `frontend/src/components/GoalModal.tsx`

- [ ] **Step 1: Create the modal component**

```tsx
// frontend/src/components/GoalModal.tsx
"use client";
import { useEffect, useRef, useState } from "react";
import { useCreateGoal } from "@/lib/queries";

interface GoalModalProps {
  onClose: () => void;
}

export function GoalModal({ onClose }: GoalModalProps) {
  const [rawInput, setRawInput] = useState("");
  const [weekday, setWeekday] = useState(2);
  const [weekend, setWeekend] = useState(4);
  const backdropRef = useRef<HTMLDivElement>(null);

  const { mutate: createGoal, isPending } = useCreateGoal(onClose);

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

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!rawInput.trim()) return;
    createGoal({
      raw_input: rawInput.trim(),
      available_hours: { weekday, weekend },
    });
  }

  return (
    <div
      ref={backdropRef}
      onClick={handleBackdropClick}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
    >
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 flex flex-col gap-5">
        <h2 className="text-xl font-extrabold text-primary">새 목표 만들기</h2>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-semibold text-on-surface-variant">
              목표를 자유롭게 입력하세요
            </label>
            <textarea
              value={rawInput}
              onChange={(e) => setRawInput(e.target.value)}
              placeholder="예: 이번 달 안에 토익 900점 받고 싶어"
              rows={3}
              className="border border-outline-variant rounded-xl px-4 py-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-semibold text-on-surface-variant">
                평일 시간 (시간/일)
              </label>
              <input
                type="number"
                min={1}
                max={12}
                value={weekday}
                onChange={(e) => setWeekday(Number(e.target.value))}
                className="border border-outline-variant rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-semibold text-on-surface-variant">
                주말 시간 (시간/일)
              </label>
              <input
                type="number"
                min={1}
                max={12}
                value={weekend}
                onChange={(e) => setWeekend(Number(e.target.value))}
                className="border border-outline-variant rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isPending || !rawInput.trim()}
            className="w-full py-3 rounded-xl bg-primary text-white font-bold text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-primary/90 transition-colors"
          >
            {isPending ? "생성 중..." : "목표 생성"}
          </button>
        </form>
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
git add src/components/GoalModal.tsx
git commit -m "feat: add GoalModal for creating goals via FAB"
```

---

### Task 7: Update page.tsx with real data

**Files:**
- Modify: `frontend/src/app/page.tsx`

Replace the entire file. Preserve the visual structure and className hierarchy exactly. Only the data source changes.

- [ ] **Step 1: Replace page.tsx**

```tsx
// frontend/src/app/page.tsx
"use client";
import Link from "next/link";
import { useState } from "react";
import { useGoals, useToggleTodo } from "@/lib/queries";
import { GoalModal } from "@/components/GoalModal";

export default function DashboardPage() {
  const [modalOpen, setModalOpen] = useState(false);
  const { data: goals = [], isLoading } = useGoals();
  const { mutate: toggleTodo } = useToggleTodo();

  const today = new Date().toISOString().slice(0, 10);
  const todayTodos = goals
    .flatMap((g) => g.milestones.flatMap((m) => m.todos))
    .filter((t) => t.due_date === today);

  const latestGoal = goals[0] ?? null;
  const milestones = latestGoal?.milestones ?? [];

  if (isLoading) {
    return (
      <div className="pt-24 px-6 text-on-surface-variant text-sm">
        로딩 중...
      </div>
    );
  }

  return (
    <>
      {/* TopAppBar */}
      <header className="fixed top-0 left-0 w-full z-50 flex justify-between items-center px-4 h-16 bg-slate-50 border-b border-slate-200 shadow-none transition-all duration-200 ease-in-out">
        <div className="flex items-center gap-3">
          <span className="material-symbols-outlined text-primary">menu</span>
          <h1 className="text-xl font-extrabold tracking-tight text-primary">
            Hierar-Do
          </h1>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm font-bold tracking-tight text-primary">
            에이전트 브리핑
          </span>
          <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center overflow-hidden border border-indigo-200">
            <span className="material-symbols-outlined text-secondary text-base">
              person
            </span>
          </div>
        </div>
      </header>

      <main className="pt-24 pb-24 px-6 max-w-[1400px] mx-auto">
        {goals.length === 0 ? (
          <div className="pt-16 text-center text-on-surface-variant">
            아직 목표가 없어요. + 버튼으로 첫 목표를 만들어보세요!
          </div>
        ) : (
          <div className="flex flex-col gap-10">
            {/* Tier 1: Daily Checklist */}
            <section className="grid grid-cols-1 md:grid-cols-12 gap-8">
              <div className="md:col-span-7">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="font-bold text-2xl text-primary border-l-4 border-primary pl-4">
                    일일 체크리스트
                  </h2>
                  <span className="text-sm text-outline font-medium">오늘</span>
                </div>
                <div className="bg-white border border-outline-variant rounded-xl divide-y divide-slate-100 shadow-md">
                  {todayTodos.length === 0 ? (
                    <div className="p-5 text-sm text-on-surface-variant text-center">
                      오늘 할 일이 없어요.
                    </div>
                  ) : (
                    todayTodos.map((todo) => (
                      <label
                        key={todo.id}
                        className="flex items-center gap-4 p-5 hover:bg-surface transition-colors cursor-pointer"
                      >
                        <input
                          checked={todo.is_done}
                          onChange={() =>
                            toggleTodo({ todoId: todo.id, isDone: !todo.is_done })
                          }
                          className="w-5 h-5 rounded border-outline text-primary-container focus:ring-primary"
                          type="checkbox"
                        />
                        <div className="flex-1">
                          <span
                            className={`text-base font-semibold ${
                              todo.is_done ? "line-through text-outline" : ""
                            }`}
                          >
                            {todo.title}
                          </span>
                        </div>
                        {todo.estimated_minutes > 0 && (
                          <span className="text-[10px] text-outline">
                            {todo.estimated_minutes}분
                          </span>
                        )}
                      </label>
                    ))
                  )}
                </div>
              </div>

              <div className="md:col-span-5 flex flex-col justify-center">
                <div className="bg-primary text-on-primary p-card-padding rounded-xl shadow-lg relative overflow-hidden">
                  <div className="absolute top-0 right-0 p-4 opacity-10">
                    <span className="material-symbols-outlined text-6xl">
                      smart_toy
                    </span>
                  </div>
                  <div className="flex items-center gap-2 mb-4">
                    <span className="material-symbols-outlined text-lg">
                      bolt
                    </span>
                    <h4 className="text-[10px] uppercase tracking-[0.15em] text-white/70 font-bold">
                      시스템 인텔리전스
                    </h4>
                  </div>
                  <p className="text-lg leading-relaxed mb-6">
                    오늘 할 일{" "}
                    <span className="font-bold underline decoration-white/30">
                      {todayTodos.filter((t) => t.is_done).length}/
                      {todayTodos.length}
                    </span>
                    개 완료.
                  </p>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-white/60 font-medium">
                      {latestGoal.title}
                    </span>
                  </div>
                </div>
              </div>
            </section>

            {/* Tier 2: Weekly Milestones */}
            <section className="relative">
              <div className="flex items-center justify-between mb-6">
                <h2 className="font-bold text-2xl text-primary">
                  주간 마일스톤
                </h2>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 relative pl-indent">
                <div className="stem-line" />
                {milestones.map((milestone) => (
                  <div key={milestone.id} className="relative">
                    <div className="stem-connector" />
                    <div className="bg-surface-container-lowest border border-outline-variant p-card-padding rounded-xl shadow-sm hover:shadow-md transition-shadow">
                      <div className="flex justify-between items-start mb-4">
                        <div className="px-2 py-0.5 rounded bg-primary-fixed text-on-primary-fixed text-[10px] font-bold">
                          {milestone.week_number}주차
                        </div>
                      </div>
                      <h4 className="font-semibold text-lg text-on-surface mb-2">
                        {milestone.title}
                      </h4>
                      <div className="flex items-center gap-4">
                        <div className="h-1 flex-1 bg-surface-container rounded-full overflow-hidden">
                          <div
                            className="h-full bg-primary"
                            style={{
                              width: `${
                                milestone.todos.length === 0
                                  ? 0
                                  : Math.round(
                                      (milestone.todos.filter((t) => t.is_done)
                                        .length /
                                        milestone.todos.length) *
                                        100
                                    )
                              }%`,
                            }}
                          />
                        </div>
                        <span className="text-xs text-outline font-bold">
                          {milestone.todos.length === 0
                            ? "0"
                            : Math.round(
                                (milestone.todos.filter((t) => t.is_done)
                                  .length /
                                  milestone.todos.length) *
                                  100
                              )}
                          %
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            {/* Tier 3: Monthly Goal */}
            <section>
              <div className="flex items-center justify-between mb-6">
                <h2 className="font-bold text-2xl text-primary">월간 목표</h2>
                <span className="text-xs font-bold bg-secondary-container text-on-secondary-container px-2 py-1 rounded">
                  {latestGoal.deadline}까지
                </span>
              </div>
              <div className="bg-surface-container-lowest border border-outline-variant p-card-padding rounded-xl relative overflow-hidden shadow-sm">
                <div className="flex items-start gap-3 mb-4">
                  <span
                    className="material-symbols-outlined text-primary"
                    style={{ fontVariationSettings: "'FILL' 1" }}
                  >
                    star
                  </span>
                  <h3 className="font-semibold text-lg text-primary">
                    {latestGoal.title}
                  </h3>
                </div>
                <p className="text-base text-on-surface-variant">
                  {latestGoal.raw_input}
                </p>
              </div>
            </section>
          </div>
        )}
      </main>

      {/* FAB */}
      <button
        onClick={() => setModalOpen(true)}
        className="fixed bottom-24 right-6 z-50 w-14 h-14 rounded-full bg-primary text-white shadow-lg flex items-center justify-center hover:bg-primary/90 transition-colors md:bottom-8"
        aria-label="새 목표 추가"
      >
        <span className="material-symbols-outlined">add</span>
      </button>

      {modalOpen && <GoalModal onClose={() => setModalOpen(false)} />}

      {/* Bottom Navigation */}
      <nav className="md:hidden fixed bottom-0 left-0 w-full z-50 flex justify-around items-center px-4 pt-2 h-20 bg-white border-t border-slate-200">
        <div className="flex flex-col items-center justify-center bg-indigo-50 text-primary rounded-xl px-3 py-1 transition-transform active:scale-95">
          <span className="material-symbols-outlined">checklist</span>
          <span className="text-[10px] font-extrabold uppercase tracking-widest">
            할 일
          </span>
        </div>
        <Link
          href="/calendar"
          className="flex flex-col items-center justify-center text-slate-400 hover:text-primary transition-transform active:scale-95"
        >
          <span className="material-symbols-outlined">flag</span>
          <span className="text-[10px] font-extrabold uppercase tracking-widest">
            목표
          </span>
        </Link>
        <div className="flex flex-col items-center justify-center text-slate-400 hover:text-primary transition-transform active:scale-95">
          <span className="material-symbols-outlined">smart_toy</span>
          <span className="text-[10px] font-extrabold uppercase tracking-widest">
            브리핑
          </span>
        </div>
        <div className="flex flex-col items-center justify-center text-slate-400 hover:text-primary transition-transform active:scale-95">
          <span className="material-symbols-outlined">settings</span>
          <span className="text-[10px] font-extrabold uppercase tracking-widest">
            설정
          </span>
        </div>
      </nav>
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

- [ ] **Step 3: Verify build succeeds**

```bash
cd frontend
npm run build 2>&1 | tail -20
```

Expected: `✓ Compiled successfully` or similar — no type errors

- [ ] **Step 4: Commit**

```bash
git add src/app/page.tsx
git commit -m "feat: connect dashboard to backend API with real data and FAB modal"
```
