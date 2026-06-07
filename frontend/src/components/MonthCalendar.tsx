"use client";
import { useState } from "react";
import type { Todo } from "@/lib/types";
import { toDateStr } from "@/lib/utils";

interface MonthCalendarProps {
  todosByDate: Record<string, Todo[]>;
  selectedDate: string | null;
  onDateSelect: (date: string) => void;
}

const TODAY_STR = toDateStr(new Date());

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
  const [currentMonth, setCurrentMonth] = useState(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1);
  });

  const year = currentMonth.getFullYear();
  const month = currentMonth.getMonth();
  const days = getCalendarDays(year, month);

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
          const isToday = dateStr === TODAY_STR;
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
