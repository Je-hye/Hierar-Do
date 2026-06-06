// frontend/src/app/page.tsx
"use client";
import Link from "next/link";
import { useState, useRef } from "react";
import {
  useGoals,
  useToggleTodo,
  useUpdateMilestone,
  useDeleteGoal,
  useUpdateGoalStatus,
  useGoalSuggest,
  useGoalApply,
} from "@/lib/queries";
import { GoalModal } from "@/components/GoalModal";
import type { Goal, Milestone } from "@/lib/types";

/** 로딩 스켈레톤 */
function SkeletonCard() {
  return (
    <div className="bg-white border border-outline-variant rounded-xl p-5 shadow-sm animate-pulse">
      <div className="h-4 bg-slate-200 rounded w-2/3 mb-3" />
      <div className="h-3 bg-slate-100 rounded w-1/2" />
    </div>
  );
}

/** 인라인 편집 가능한 마일스톤 제목 */
function EditableMilestoneTitle({ milestone }: { milestone: Milestone }) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(milestone.title);
  const inputRef = useRef<HTMLInputElement>(null);
  const { mutate: updateMilestone } = useUpdateMilestone();

  function startEdit() {
    setValue(milestone.title);
    setEditing(true);
    setTimeout(() => inputRef.current?.focus(), 0);
  }

  function commit() {
    if (value.trim() && value.trim() !== milestone.title) {
      updateMilestone({ milestoneId: milestone.id, data: { title: value.trim() } });
    }
    setEditing(false);
  }

  return editing ? (
    <input
      ref={inputRef}
      value={value}
      onChange={(e) => setValue(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === "Enter") commit();
        if (e.key === "Escape") { setEditing(false); setValue(milestone.title); }
      }}
      className="font-semibold text-lg text-on-surface border-b border-primary outline-none bg-transparent w-full"
    />
  ) : (
    <h4
      className="font-semibold text-lg text-on-surface cursor-text"
      onDoubleClick={startEdit}
      title="더블클릭하여 편집"
    >
      {milestone.title}
    </h4>
  );
}

/** 목표 카드 (월간 목표 섹션) */
function GoalCard({ goal }: { goal: Goal }) {
  const { mutate: deleteGoal, isPending: isDeleting } = useDeleteGoal();
  const { mutate: updateStatus } = useUpdateGoalStatus();

  const totalTodos = goal.milestones.flatMap((m) => m.todos).length;
  const doneTodos = goal.milestones.flatMap((m) => m.todos).filter((t) => t.is_done).length;
  const pct = totalTodos === 0 ? 0 : Math.round((doneTodos / totalTodos) * 100);
  const isDone = goal.status === "done";

  return (
    <div
      className={`border border-outline-variant p-card-padding rounded-xl relative overflow-hidden shadow-sm transition-opacity ${
        isDone ? "bg-slate-50 opacity-70" : "bg-surface-container-lowest"
      }`}
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-start gap-3 flex-1 min-w-0">
          <span
            className={`material-symbols-outlined shrink-0 ${isDone ? "text-slate-400" : "text-primary"}`}
            style={{ fontVariationSettings: "'FILL' 1" }}
          >
            {isDone ? "check_circle" : "star"}
          </span>
          <div className="flex-1 min-w-0">
            <h3 className={`font-semibold text-lg truncate ${isDone ? "line-through text-slate-400" : "text-primary"}`}>
              {goal.title}
            </h3>
            <p className="text-sm text-on-surface-variant mt-0.5 line-clamp-2">{goal.raw_input}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-xs font-bold bg-secondary-container text-on-secondary-container px-2 py-1 rounded">
            {goal.deadline}까지
          </span>
          {/* 완료 토글 버튼 */}
          <button
            onClick={() =>
              updateStatus({ goalId: goal.id, status: isDone ? "active" : "done" })
            }
            className={`text-xs font-bold px-2 py-1 rounded border transition-colors ${
              isDone
                ? "border-slate-300 text-slate-400 hover:border-primary hover:text-primary"
                : "border-primary/30 text-primary hover:bg-primary hover:text-white"
            }`}
            title={isDone ? "활성화" : "완료 처리"}
          >
            {isDone ? "재개" : "완료"}
          </button>
          {/* 삭제 버튼 */}
          <button
            onClick={() => {
              if (confirm(`"${goal.title}" 목표와 모든 하위 항목을 삭제할까요?`)) {
                deleteGoal(goal.id);
              }
            }}
            disabled={isDeleting}
            className="p-1 rounded hover:bg-red-50 text-outline hover:text-red-500 transition-colors"
            title="목표 삭제"
          >
            <span className="material-symbols-outlined text-base">delete</span>
          </button>
        </div>
      </div>
      {/* 전체 진척률 바 */}
      <div className="flex items-center gap-3 mt-2">
        <div className="h-1.5 flex-1 bg-slate-100 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${isDone ? "bg-slate-400" : "bg-primary"}`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className="text-xs text-outline font-bold shrink-0">
          {doneTodos}/{totalTodos} ({pct}%)
        </span>
      </div>
    </div>
  );
}

/** 에이전트 브리핑 카드 내부 콘텐츠 (AI 진단) */
function AgentBriefing({ targetGoal }: { targetGoal: Goal }) {
  const { mutate: suggest, data: suggestion, isPending: isSuggesting } = useGoalSuggest();
  const { mutate: apply, isPending: isApplying } = useGoalApply();

  function handleApply() {
    if (!suggestion) return;
    apply(
      {
        goalId: targetGoal.id,
        data: {
          items: suggestion.suggestions.map((s) => ({
            todo_id: s.todo_id,
            new_due_date: s.suggested_due_date,
          })),
        },
      },
      {
        onSuccess: () => {
          alert("재조정 제안이 적용되었습니다.");
        },
      }
    );
  }

  if (suggestion) {
    return (
      <div className="flex flex-col gap-3 mt-4 border-t border-white/20 pt-4 relative z-10">
        <div className="flex items-start gap-2 bg-white/10 p-3 rounded-lg">
          <span className="material-symbols-outlined text-white">lightbulb</span>
          <div className="text-sm w-full">
            <p className="font-bold mb-2">{suggestion.overall_summary}</p>
            {suggestion.suggestions.length > 0 ? (
              <ul className="text-xs space-y-2 mt-2">
                {suggestion.suggestions.map((s) => (
                  <li key={s.todo_id} className="bg-white/5 p-2 rounded">
                    <div className="font-semibold mb-1 truncate" title={s.title}>
                      {s.title}
                    </div>
                    <div className="flex items-center gap-1 opacity-75 mb-1">
                      <span>{s.current_due_date || "미정"}</span>
                      <span className="material-symbols-outlined text-[10px]">arrow_forward</span>
                      <span className="text-secondary-container font-bold">
                        {s.suggested_due_date}
                      </span>
                    </div>
                    <div className="text-[10px] leading-relaxed opacity-90">{s.reason}</div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs opacity-80 mt-1">변경이 필요한 일정이 없습니다.</p>
            )}
          </div>
        </div>
        {suggestion.suggestions.length > 0 && (
          <button
            onClick={handleApply}
            disabled={isApplying}
            className="bg-secondary-container text-on-secondary-container text-sm font-bold py-2 rounded-lg hover:brightness-110 transition-all shadow-md disabled:opacity-50"
          >
            {isApplying ? "적용 중..." : "제안 승인 및 적용"}
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="flex items-center justify-between mt-6 relative z-10">
      <span className="text-xs text-white/60 font-medium truncate pr-2">
        {targetGoal.title}
      </span>
      <button
        onClick={() => suggest(targetGoal.id)}
        disabled={isSuggesting}
        className="text-xs font-bold bg-white/20 hover:bg-white/30 px-3 py-1.5 rounded transition-colors whitespace-nowrap disabled:opacity-50"
      >
        {isSuggesting ? "진단 중..." : "AI 진단받기"}
      </button>
    </div>
  );
}

export default function DashboardPage() {
  const [modalOpen, setModalOpen] = useState(false);
  const [toastVisible, setToastVisible] = useState(false);
  const { data: goals = [], isLoading } = useGoals();
  const { mutate: toggleTodo } = useToggleTodo();

  const today = new Intl.DateTimeFormat("sv").format(new Date());
  const todayTodos = goals
    .flatMap((g) => g.milestones.flatMap((m) => m.todos))
    .filter((t) => t.due_date === today)
    .sort((a, b) => Number(a.is_done) - Number(b.is_done));

  // 활성 목표와 완료 목표 분리
  const activeGoals = goals.filter((g) => g.status !== "done");
  const doneGoals = goals.filter((g) => g.status === "done");
  const latestGoal = activeGoals[0] ?? goals[0];

  function showComingSoon() {
    setToastVisible(true);
    setTimeout(() => setToastVisible(false), 2000);
  }

  return (
    <>
      {/* TopAppBar */}
      <header className="fixed top-0 left-0 w-full z-50 flex justify-between items-center px-4 h-16 bg-slate-50 border-b border-slate-200">
        <div className="flex items-center gap-3">
          <Link href="/calendar" aria-label="캘린더 보기" className="hover:opacity-70 transition-opacity">
            <span className="material-symbols-outlined text-primary">calendar_month</span>
          </Link>
          <h1 className="text-xl font-extrabold tracking-tight text-primary">Hierar-Do</h1>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm font-bold tracking-tight text-primary">에이전트 브리핑</span>
          <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center overflow-hidden border border-indigo-200">
            <span className="material-symbols-outlined text-secondary text-base">person</span>
          </div>
        </div>
      </header>

      <main className="pt-24 pb-24 px-6 max-w-[1400px] mx-auto">
        {isLoading ? (
          <div className="flex flex-col gap-10">
            <section>
              <div className="h-7 bg-slate-200 rounded w-40 mb-6 animate-pulse" />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <SkeletonCard /><SkeletonCard />
              </div>
            </section>
            <section>
              <div className="h-7 bg-slate-200 rounded w-36 mb-6 animate-pulse" />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <SkeletonCard /><SkeletonCard /><SkeletonCard /><SkeletonCard />
              </div>
            </section>
          </div>
        ) : goals.length === 0 ? (
          <div className="pt-16 text-center text-on-surface-variant">
            아직 목표가 없어요. + 버튼으로 첫 목표를 만들어보세요!
          </div>
        ) : (
          <div className="flex flex-col gap-10">
            {/* 일일 체크리스트 */}
            <section>
              <div className="flex items-center justify-between mb-6">
                <h2 className="font-bold text-2xl text-primary border-l-4 border-primary pl-4">일일 체크리스트</h2>
                <span className="text-sm text-outline font-medium">오늘</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-white border border-outline-variant rounded-xl divide-y divide-slate-100 shadow-md">
                  {todayTodos.length === 0 ? (
                    <div className="p-5 text-sm text-on-surface-variant text-center">오늘 할 일이 없어요.</div>
                  ) : (
                    todayTodos.map((todo) => (
                      <label
                        key={todo.id}
                        className="flex items-center gap-4 p-5 hover:bg-surface transition-colors cursor-pointer"
                      >
                        <input
                          checked={todo.is_done}
                          onChange={() => toggleTodo({ todoId: todo.id, isDone: !todo.is_done })}
                          className="w-5 h-5 rounded border-outline text-primary-container focus:ring-primary"
                          type="checkbox"
                        />
                        <div className="flex-1">
                          <span className={`text-base font-semibold ${todo.is_done ? "line-through text-outline" : ""}`}>
                            {todo.title}
                          </span>
                        </div>
                        {todo.estimated_minutes > 0 && (
                          <span className="text-[10px] text-outline">{todo.estimated_minutes}분</span>
                        )}
                      </label>
                    ))
                  )}
                </div>
                {/* AI 브리핑 카드 */}
                {latestGoal && (
                  <div className="bg-primary text-on-primary p-card-padding rounded-xl shadow-lg relative overflow-hidden">
                    <div className="absolute top-0 right-0 p-4 opacity-10">
                      <span className="material-symbols-outlined text-6xl">smart_toy</span>
                    </div>
                    <div className="flex items-center gap-2 mb-4">
                      <span className="material-symbols-outlined text-lg">bolt</span>
                      <h4 className="text-[10px] uppercase tracking-[0.15em] text-white/70 font-bold">시스템 인텔리전스</h4>
                    </div>
                    <p className="text-lg leading-relaxed mb-6">
                      오늘 할 일{" "}
                      <span className="font-bold underline decoration-white/30">
                        {todayTodos.filter((t) => t.is_done).length}/{todayTodos.length}
                      </span>
                      개 완료.
                    </p>
                    <AgentBriefing targetGoal={latestGoal} />
                  </div>
                )}
              </div>
            </section>

            {/* 주간 마일스톤 */}
            {activeGoals.length > 0 && (
              <section>
                <h2 className="font-bold text-2xl text-primary mb-6">주간 마일스톤</h2>
                <div className="flex flex-col gap-8">
                  {activeGoals.map((goal) => (
                    <div key={goal.id}>
                      <p className="text-sm font-semibold text-outline mb-3">{goal.title}</p>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {goal.milestones.map((milestone) => {
                          const pct =
                            milestone.todos.length === 0
                              ? 0
                              : Math.round(
                                  (milestone.todos.filter((t) => t.is_done).length /
                                    milestone.todos.length) * 100
                                );
                          return (
                            <div
                              key={milestone.id}
                              className="group bg-surface-container-lowest border border-outline-variant p-card-padding rounded-xl shadow-sm hover:shadow-md transition-shadow"
                            >
                              <div className="flex items-start justify-between mb-3">
                                <div className="px-2 py-0.5 rounded bg-primary-fixed text-on-primary-fixed text-[10px] font-bold inline-block">
                                  {milestone.week_number}주차
                                </div>
                              </div>
                              {/* 마일스톤 제목 — 더블클릭 인라인 편집 */}
                              <EditableMilestoneTitle milestone={milestone} />
                              <div className="flex items-center gap-4 mt-4">
                                <div className="h-1 flex-1 bg-surface-container rounded-full overflow-hidden">
                                  <div className="h-full bg-primary" style={{ width: `${pct}%` }} />
                                </div>
                                <span className="text-xs text-outline font-bold">{pct}%</span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* 월간 목표 */}
            <section>
              <h2 className="font-bold text-2xl text-primary mb-6">월간 목표</h2>
              <div className="flex flex-col gap-4">
                {activeGoals.map((goal) => (
                  <GoalCard key={goal.id} goal={goal} />
                ))}
              </div>
            </section>

            {/* 완료된 목표 (접힘 섹션) */}
            {doneGoals.length > 0 && (
              <section>
                <details className="group">
                  <summary className="cursor-pointer flex items-center gap-2 font-bold text-lg text-slate-400 mb-4 select-none">
                    <span className="material-symbols-outlined text-slate-300 group-open:rotate-90 transition-transform">
                      chevron_right
                    </span>
                    완료한 목표 ({doneGoals.length}개)
                  </summary>
                  <div className="flex flex-col gap-4 mt-2">
                    {doneGoals.map((goal) => (
                      <GoalCard key={goal.id} goal={goal} />
                    ))}
                  </div>
                </details>
              </section>
            )}
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

      {/* 준비 중 토스트 */}
      {toastVisible && (
        <div className="fixed bottom-28 left-1/2 -translate-x-1/2 z-50 bg-slate-800 text-white text-xs font-semibold px-4 py-2 rounded-full shadow-lg md:bottom-12">
          준비 중인 기능이에요 🚧
        </div>
      )}

      {/* Bottom Navigation */}
      <nav className="md:hidden fixed bottom-0 left-0 w-full z-50 flex justify-around items-center px-4 pt-2 h-20 bg-white border-t border-slate-200">
        <div className="flex flex-col items-center justify-center bg-indigo-50 text-primary rounded-xl px-3 py-1">
          <span className="material-symbols-outlined">checklist</span>
          <span className="text-[10px] font-extrabold uppercase tracking-widest">할 일</span>
        </div>
        <Link href="/calendar" className="flex flex-col items-center justify-center text-slate-400 hover:text-primary">
          <span className="material-symbols-outlined">flag</span>
          <span className="text-[10px] font-extrabold uppercase tracking-widest">목표</span>
        </Link>
        <button onClick={showComingSoon} className="flex flex-col items-center justify-center text-slate-300">
          <span className="material-symbols-outlined">smart_toy</span>
          <span className="text-[10px] font-extrabold uppercase tracking-widest">브리핑</span>
        </button>
        <button onClick={showComingSoon} className="flex flex-col items-center justify-center text-slate-300">
          <span className="material-symbols-outlined">settings</span>
          <span className="text-[10px] font-extrabold uppercase tracking-widest">설정</span>
        </button>
      </nav>
    </>
  );
}
