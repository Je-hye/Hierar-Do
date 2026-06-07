# Calendar View — Design Spec
**Date:** 2026-04-27
**Status:** Approved

---

## Overview

AI가 생성한 할 일(todo)들을 `due_date` 기준으로 월간 캘린더에서 시각화하고, 날짜 클릭 시 해당 주의 상세 일정을 아래에 표시한다. 기존 하드코딩 `/calendar` 페이지를 실제 데이터로 교체한다.

---

## Scope

**변경 대상:**
- `frontend/src/app/calendar/page.tsx` — 실제 데이터 연결, 새 컴포넌트 조합
- `frontend/src/app/page.tsx` — 메뉴 아이콘을 `/calendar` 링크로 변경

**신규 파일:**
- `frontend/src/components/MonthCalendar.tsx`
- `frontend/src/components/WeekDetail.tsx`

---

## File Structure

```
frontend/src/
├── components/
│   ├── MonthCalendar.tsx   (신규) 월간 그리드 캘린더
│   └── WeekDetail.tsx      (신규) 주간 드릴다운 패널
└── app/
    ├── calendar/
    │   └── page.tsx        (수정) 하드코딩 → 실제 데이터
    └── page.tsx            (수정) 메뉴 아이콘 → /calendar 링크
```

---

## Data Flow

`useGoals()` → 전체 goals → milestones → todos 플래튼 → `due_date` 기준 그룹화.

```ts
// 날짜별 todo 맵
const todosByDate: Record<string, Todo[]> = {};
goals
  .flatMap(g => g.milestones.flatMap(m => m.todos))
  .filter(t => t.due_date !== null)
  .forEach(t => {
    todosByDate[t.due_date!] ??= [];
    todosByDate[t.due_date!].push(t);
  });
```

---

## MonthCalendar (`src/components/MonthCalendar.tsx`)

**Props:**
```ts
interface MonthCalendarProps {
  todosByDate: Record<string, Todo[]>;
  selectedDate: string | null;       // "YYYY-MM-DD"
  onDateSelect: (date: string) => void;
}
```

**렌더링:**
- 상단: `< 2026년 4월 >` 이전/다음 달 버튼 + 현재 월/연도
- 7열 헤더: 일 월 화 수 목 금 토
- 날짜 셀:
  - 날짜 숫자
  - 해당 날짜에 todo가 있으면 `bg-primary` 작은 점(•)
  - 오늘 날짜: `border border-primary` 강조
  - 선택된 날짜: `bg-primary text-white rounded-full`
- 클릭 시 `onDateSelect("YYYY-MM-DD")` 호출

**내부 상태:** `currentMonth: Date` (이전/다음 달 이동용)

---

## WeekDetail (`src/components/WeekDetail.tsx`)

**Props:**
```ts
interface WeekDetailProps {
  selectedDate: string;              // "YYYY-MM-DD"
  todosByDate: Record<string, Todo[]>;
  onToggle: (todoId: number, isDone: boolean) => void;
}
```

**렌더링:**
- 선택된 날짜가 속한 주(월요일~일요일) 계산
- 7개 날짜 컬럼 가로 스크롤 (`overflow-x-auto`, 모바일 대응)
- 각 컬럼:
  - 날짜 헤더 (예: "화\n29")
  - 선택된 날짜 컬럼 강조
  - 해당 날짜의 todo 카드 목록 (체크박스 + 제목 + estimated_minutes)
- 주 전체에 todo가 없으면: "이 주에는 할 일이 없어요." 안내 문구

---

## Calendar Page (`src/app/calendar/page.tsx`)

- `"use client"` 디렉티브
- `useGoals()`, `useToggleTodo()` 훅 사용
- `selectedDate: string | null` 상태 관리 (기본값: 오늘)
- 헤더: 기존 TopAppBar 스타일 유지, `← 돌아가기` 버튼 → `<Link href="/">`
- `<MonthCalendar>` 렌더링
- `selectedDate`가 있으면 `<WeekDetail>` 렌더링 (캘린더 아래)
- 로딩 중: "로딩 중..." 텍스트

---

## Dashboard Page (`src/app/page.tsx`)

헤더의 `menu` 아이콘을 `<Link href="/calendar">` 로 감싼다.

```tsx
// 변경 전
<span className="material-symbols-outlined text-primary">menu</span>

// 변경 후
<Link href="/calendar">
  <span className="material-symbols-outlined text-primary">menu</span>
</Link>
```

---

## MVP 제외

- 할 일 생성/편집 (캘린더에서 직접)
- 드래그 앤 드롭으로 날짜 변경
- 목표별 색상 구분
