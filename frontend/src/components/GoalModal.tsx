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
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const backdropRef = useRef<HTMLDivElement>(null);

  const { mutate: createGoal, isPending } = useCreateGoal(onClose);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // 생성 중에는 Escape 키로 닫기 방지 (#15)
      if (e.key === "Escape" && !isPending) onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose, isPending]);

  function handleBackdropClick(e: React.MouseEvent) {
    // 생성 중에는 백드롭 클릭으로 닫기 방지 (#15)
    if (!isPending && e.target === backdropRef.current) onClose();
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!rawInput.trim()) return;
    setErrorMsg(null);
    createGoal(
      { raw_input: rawInput.trim(), available_hours: { weekday, weekend } },
      {
        onError: (err: Error) => {
          // 백엔드 detail 메시지를 사용자에게 직접 표시 (#16)
          setErrorMsg(err.message || "목표 생성 중 오류가 발생했어요. 다시 시도해 주세요.");
        },
      }
    );
  }

  return (
    <div
      ref={backdropRef}
      onClick={handleBackdropClick}
      className={`fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4 ${isPending ? "cursor-not-allowed" : ""}`}
    >
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 flex flex-col gap-5">
        <h2 className="text-xl font-extrabold text-primary">새 목표 만들기</h2>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="raw-input" className="text-sm font-semibold text-on-surface-variant">
              목표를 자유롭게 입력하세요
            </label>
            <textarea
              id="raw-input"
              value={rawInput}
              onChange={(e) => setRawInput(e.target.value)}
              placeholder="예: 이번 달 안에 토익 900점 받고 싶어"
              rows={3}
              disabled={isPending}
              className="border border-outline-variant rounded-xl px-4 py-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-60"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1.5">
              <label htmlFor="weekday-hours" className="text-sm font-semibold text-on-surface-variant">
                평일 시간 (시간/일)
              </label>
              <input
                id="weekday-hours"
                type="number"
                min={1}
                max={24}
                value={weekday}
                disabled={isPending}
                onChange={(e) => setWeekday(Math.min(24, Math.max(1, Number(e.target.value))))}
                className="border border-outline-variant rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-60"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label htmlFor="weekend-hours" className="text-sm font-semibold text-on-surface-variant">
                주말 시간 (시간/일)
              </label>
              <input
                id="weekend-hours"
                type="number"
                min={1}
                max={24}
                value={weekend}
                disabled={isPending}
                onChange={(e) => setWeekend(Math.min(24, Math.max(1, Number(e.target.value))))}
                className="border border-outline-variant rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-60"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isPending || !rawInput.trim()}
            className="w-full py-3 rounded-xl bg-primary text-white font-bold text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-primary/90 transition-colors"
          >
            {isPending ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                AI가 일정을 생성하는 중...
              </span>
            ) : (
              "목표 생성"
            )}
          </button>

          {errorMsg && (
            <p className="text-sm text-error text-center bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {errorMsg}
            </p>
          )}
        </form>
      </div>
    </div>
  );
}
