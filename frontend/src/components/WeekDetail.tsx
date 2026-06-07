// frontend/src/components/WeekDetail.tsx
"use client";
import { useState, useRef } from "react";
import type { Milestone, Todo } from "@/lib/types";
import { toDateStr } from "@/lib/utils";
import {
  useToggleTodo,
  useUpdateTodo,
  useDeleteTodo,
  useCreateTodo,
} from "@/lib/queries";

interface WeekDetailProps {
  selectedDate: string;
  milestones: Milestone[];  // 목표의 마일스톤 목록 (todo 추가 시 milestone_id 필요)
  todosByDate: Record<string, Todo[]>;
}

const DAY_LABELS = ["월", "화", "수", "목", "금", "토", "일"];

function getWeekDays(dateStr: string): Date[] {
  const [y, m, d] = dateStr.split("-").map(Number);
  const date = new Date(y, m - 1, d);
  const day = date.getDay();
  const diffToMonday = day === 0 ? -6 : 1 - day;
  const monday = new Date(y, m - 1, d + diffToMonday);
  return Array.from({ length: 7 }, (_, i) => {
    const dt = new Date(monday);
    dt.setDate(monday.getDate() + i);
    return dt;
  });
}

/** 인라인 편집 가능한 Todo 아이템 */
function TodoItem({ todo, onMilestoneIdNeeded }: { todo: Todo; onMilestoneIdNeeded?: () => number | null }) {
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState(todo.title);
  const inputRef = useRef<HTMLInputElement>(null);

  const { mutate: toggle } = useToggleTodo();
  const { mutate: updateTodo } = useUpdateTodo();
  const { mutate: deleteTodo } = useDeleteTodo();

  function startEdit() {
    setEditValue(todo.title);
    setEditing(true);
    setTimeout(() => inputRef.current?.focus(), 0);
  }

  function commitEdit() {
    if (editValue.trim() && editValue.trim() !== todo.title) {
      updateTodo({ todoId: todo.id, data: { title: editValue.trim() } });
    }
    setEditing(false);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter") commitEdit();
    if (e.key === "Escape") { setEditing(false); setEditValue(todo.title); }
  }

  return (
    <div className="group flex items-start gap-2 p-2 bg-white border border-outline-variant rounded-lg hover:bg-surface transition-colors">
      <input
        type="checkbox"
        checked={todo.is_done}
        onChange={() => toggle({ todoId: todo.id, isDone: !todo.is_done })}
        className="mt-0.5 w-4 h-4 rounded border-outline text-primary focus:ring-primary shrink-0"
      />
      <div className="flex-1 min-w-0">
        {editing ? (
          <input
            ref={inputRef}
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            onBlur={commitEdit}
            onKeyDown={handleKeyDown}
            className="w-full text-xs font-semibold border-b border-primary outline-none bg-transparent"
          />
        ) : (
          <span
            className={`text-xs font-semibold block truncate cursor-text ${
              todo.is_done ? "line-through text-outline" : "text-on-surface"
            }`}
            onDoubleClick={startEdit}
            title="더블클릭하여 편집"
          >
            {todo.title}
          </span>
        )}
        {todo.estimated_minutes > 0 && (
          <span className="text-[10px] text-outline">{todo.estimated_minutes}분</span>
        )}
      </div>
      {/* 편집/삭제 버튼 — hover 시 노출 */}
      <div className="opacity-0 group-hover:opacity-100 flex items-center gap-1 transition-opacity shrink-0">
        <button
          onClick={startEdit}
          className="p-0.5 rounded hover:bg-primary/10 text-outline hover:text-primary transition-colors"
          title="편집"
        >
          <span className="material-symbols-outlined text-sm">edit</span>
        </button>
        <button
          onClick={() => {
            if (confirm(`"${todo.title}" 할 일을 삭제할까요?`)) {
              deleteTodo(todo.id);
            }
          }}
          className="p-0.5 rounded hover:bg-red-50 text-outline hover:text-red-500 transition-colors"
          title="삭제"
        >
          <span className="material-symbols-outlined text-sm">delete</span>
        </button>
      </div>
    </div>
  );
}

/** 날짜별 할 일 추가 폼 */
function AddTodoForm({
  dateStr,
  milestones,
  onClose,
}: {
  dateStr: string;
  milestones: Milestone[];
  onClose: () => void;
}) {
  const [title, setTitle] = useState("");
  const [milestoneId, setMilestoneId] = useState<number>(milestones[0]?.id ?? 0);
  const { mutate: createTodo, isPending } = useCreateTodo();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim() || !milestoneId) return;
    createTodo(
      { milestone_id: milestoneId, title: title.trim(), due_date: dateStr, estimated_minutes: 30 },
      { onSuccess: onClose }
    );
  }

  return (
    <form onSubmit={handleSubmit} className="mt-1 flex flex-col gap-1">
      <input
        autoFocus
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        onKeyDown={(e) => e.key === "Escape" && onClose()}
        placeholder="할 일 입력..."
        className="w-full text-xs border border-primary rounded px-2 py-1 outline-none"
      />
      {milestones.length > 1 && (
        <select
          value={milestoneId}
          onChange={(e) => setMilestoneId(Number(e.target.value))}
          className="text-[10px] border border-outline-variant rounded px-1 py-0.5"
        >
          {milestones.map((ms) => (
            <option key={ms.id} value={ms.id}>
              {ms.week_number}주차: {ms.title}
            </option>
          ))}
        </select>
      )}
      <div className="flex gap-1">
        <button
          type="submit"
          disabled={isPending || !title.trim()}
          className="flex-1 text-[10px] bg-primary text-white rounded py-0.5 disabled:opacity-50"
        >
          추가
        </button>
        <button
          type="button"
          onClick={onClose}
          className="flex-1 text-[10px] border border-outline-variant rounded py-0.5"
        >
          취소
        </button>
      </div>
    </form>
  );
}

export function WeekDetail({ selectedDate, milestones, todosByDate }: WeekDetailProps) {
  const [addingDate, setAddingDate] = useState<string | null>(null);
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
      {!hasAnyTodo && addingDate === null ? (
        <div className="text-sm text-on-surface-variant text-center py-8">
          이 주에는 할 일이 없어요.{" "}
          <button
            onClick={() => setAddingDate(toDateStr(weekDays[0]))}
            className="text-primary underline"
          >
            추가하기
          </button>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <div className="grid grid-cols-7 gap-3 min-w-[700px]">
            {weekDays.map((day, i) => {
              const dateStr = toDateStr(day);
              const isSelected = dateStr === selectedDate;
              const todos = [...(todosByDate[dateStr] ?? [])].sort(
                (a, b) => Number(a.is_done) - Number(b.is_done)
              );
              const isAdding = addingDate === dateStr;
              return (
                <div key={dateStr}>
                  <div
                    className={`text-center mb-2 py-1 rounded-lg ${
                      isSelected ? "bg-primary text-white" : "text-on-surface"
                    }`}
                  >
                    <div className="text-[10px] font-bold">{DAY_LABELS[i]}</div>
                    <div className="text-sm font-bold">{day.getDate()}</div>
                  </div>
                  <div className="flex flex-col gap-2">
                    {todos.length === 0 && !isAdding && (
                      <span className="text-[10px] text-on-surface-variant text-center block pt-2">
                        —
                      </span>
                    )}
                    {todos.map((todo) => (
                      <TodoItem key={todo.id} todo={todo} />
                    ))}
                    {isAdding && milestones.length > 0 ? (
                      <AddTodoForm
                        dateStr={dateStr}
                        milestones={milestones}
                        onClose={() => setAddingDate(null)}
                      />
                    ) : (
                      <button
                        onClick={() => setAddingDate(dateStr)}
                        className="text-[10px] text-outline hover:text-primary flex items-center gap-0.5 justify-center mt-1 opacity-0 hover:opacity-100 group-hover:opacity-100 transition-opacity"
                        title="할 일 추가"
                      >
                        <span className="material-symbols-outlined text-sm">add</span>
                      </button>
                    )}
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
