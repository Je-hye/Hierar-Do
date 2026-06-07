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

const TODAY_STR = new Intl.DateTimeFormat("sv").format(new Date()); // 로컬 타임존 YYYY-MM-DD

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
