// frontend/src/app/calendar/page.tsx
"use client";
import Link from "next/link";
import { useMemo, useState } from "react";
import { useGoals, useReschedulePreview, useRescheduleApply } from "@/lib/queries";
import { MonthCalendar } from "@/components/MonthCalendar";
import { WeekDetail } from "@/components/WeekDetail";
import { RescheduleModal } from "@/components/RescheduleModal";
import type { Milestone, RescheduleItem, Todo } from "@/lib/types";

export default function CalendarPage() {
  const [selectedDate, setSelectedDate] = useState<string>(() => {
    const offset = new Date().getTimezoneOffset();
    const date = new Date(new Date().getTime() - offset * 60 * 1000);
    return date.toISOString().split("T")[0];
  });
  const [rescheduleItems, setRescheduleItems] = useState<RescheduleItem[] | null>(null);
  const [noChanges, setNoChanges] = useState(false);

  const { data: goals = [], isLoading } = useGoals();
  const { mutate: previewReschedule, isPending: isPreviewing } = useReschedulePreview();
  const { mutate: applyReschedule, isPending: isApplying } = useRescheduleApply();

  // 모든 마일스톤을 평탄화 (할 일 추가 시 milestone 선택에 사용)
  const allMilestones = useMemo<Milestone[]>(
    () => goals.flatMap((g) => g.milestones),
    [goals]
  );

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
              milestones={allMilestones}
              todosByDate={todosByDate}
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
