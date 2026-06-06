// frontend/src/lib/types.ts
export type GoalStatus = "active" | "done" | "archived";
export type MilestoneStatus = "active" | "done";

export interface UserOut {
  id: number;
  email: string;
  available_hours: {
    weekday: number;
    weekend: number;
  };
}

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
  available_hours_weekday: number | null;
  available_hours_weekend: number | null;
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

export interface RescheduleItem {
  todo_id: number;
  title: string;
  old_due_date: string | null;
  new_due_date: string;
}

// ── 편집/생성 요청 타입 ─────────────────────────────────────────────────────

export interface UpdateTodoRequest {
  title?: string;
  due_date?: string | null;
  estimated_minutes?: number;
}

export interface CreateTodoRequest {
  milestone_id: number;
  title: string;
  due_date?: string | null;
  estimated_minutes?: number;
}

export interface UpdateMilestoneRequest {
  title?: string;
}

// ── AI 재조정 제안 타입 ─────────────────────────────────────────────────────

export interface TodoSuggestion {
  todo_id: number;
  title: string;
  current_due_date: string | null;
  suggested_due_date: string;
  reason: string;
}

export interface SuggestionResponse {
  goal_id: number;
  overall_summary: string;
  at_risk: boolean;
  suggestions: TodoSuggestion[];
}

export interface ApplySuggestionItem {
  todo_id: number;
  new_due_date: string;
}

export interface ApplySuggestionRequest {
  items: ApplySuggestionItem[];
}
