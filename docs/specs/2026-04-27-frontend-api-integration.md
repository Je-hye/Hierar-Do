# Frontend API Integration — Design Spec
**Date:** 2026-04-27
**Status:** Approved

---

## Overview

현재 프론트엔드(`page.tsx`)는 하드코딩된 더미 데이터로 구성되어 있다. 이 작업은 백엔드 REST API와 연결해 실제 데이터를 표시하고, FAB 버튼으로 목표를 생성할 수 있게 한다.

---

## Scope

**변경 대상:** `src/app/page.tsx` (메인 대시보드)
**변경 없음:** `src/app/calendar/page.tsx` (MVP 이후)

---

## File Structure

```
frontend/src/
├── lib/
│   ├── api.ts          (기존 — 수정 없음)
│   ├── types.ts        (신규) 백엔드 스키마 TypeScript 타입
│   └── queries.ts      (신규) TanStack Query 훅
├── components/
│   └── GoalModal.tsx   (신규) 목표 생성 모달
└── app/
    └── page.tsx        (수정) 하드코딩 → 실제 API 데이터
```

---

## Types (`src/lib/types.ts`)

백엔드 응답과 1:1 매핑:

```ts
export type GoalStatus = "pending" | "active" | "done";

export interface Todo {
  id: number;
  milestone_id: number;
  title: string;
  due_date: string | null;   // "YYYY-MM-DD"
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
  deadline: string;          // "YYYY-MM-DD"
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

---

## Query Hooks (`src/lib/queries.ts`)

TanStack Query v5 기반:

- `useGoals()` — `GET /api/v1/goals`, staleTime 30초
- `useCreateGoal()` — `POST /api/v1/goals`, 성공 시 goals 쿼리 무효화
- `useToggleTodo(todoId, isDone)` — `PATCH /api/v1/todos/{id}/done|undone`, 성공 시 goals 쿼리 무효화

---

## GoalModal (`src/components/GoalModal.tsx`)

FAB `+` 클릭 시 열리는 모달:

- `textarea` — 자연어 목표 입력 (raw_input)
- `평일 시간` 숫자 입력 (weekday, 기본값 2)
- `주말 시간` 숫자 입력 (weekend, 기본값 4)
- 제출 버튼 — `useCreateGoal` 호출, 로딩 중 비활성화 + "생성 중..." 텍스트
- 외부 클릭 또는 ESC로 닫기

---

## Main Page (`src/app/page.tsx`)

| 섹션 | 데이터 소스 |
|------|------------|
| 일일 체크리스트 | `goals`에서 전체 todos 수집 → `due_date === 오늘` 필터 |
| 할 일 체크박스 | `useToggleTodo` 호출 (낙관적 업데이트 없이 단순 refetch) |
| 주간 마일스톤 | `goals[0].milestones` (최신 목표 기준) |
| 월간 목표 | `goals[0]` title + deadline |
| FAB | `GoalModal` open/close 상태 관리 |

**로딩 상태:** "로딩 중..." 텍스트
**빈 상태:** 목표 없을 때 "아직 목표가 없어요. + 버튼으로 첫 목표를 만들어보세요!" 안내

`"use client"` 디렉티브 필요 (TanStack Query 클라이언트 훅 사용).

---

## QueryClient Provider

TanStack Query 사용을 위해 `src/app/layout.tsx`에 `QueryClientProvider` 래핑 추가. 기존 레이아웃 구조 유지.

---

## MVP 제외

- 에러 토스트 (콘솔 로그만)
- 낙관적 업데이트
- calendar/page.tsx API 연결
- 페이지네이션
