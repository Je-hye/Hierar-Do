// frontend/src/lib/queries.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  CreateGoalRequest,
  CreateGoalResponse,
  CreateTodoRequest,
  Goal,
  RescheduleItem,
  SuggestionResponse,
  ApplySuggestionRequest,
  Todo,
  UpdateMilestoneRequest,
  UpdateTodoRequest,
} from "@/lib/types";

// ── Goals ────────────────────────────────────────────────────────────────────

export function useGoals() {
  return useQuery<Goal[]>({
    queryKey: ["goals"],
    queryFn: () => api.get<Goal[]>("/api/v1/goals"),
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

export function useDeleteGoal() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, number>({
    mutationFn: (goalId) => api.delete(`/api/v1/goals/${goalId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["goals"] }),
  });
}

export function useUpdateGoalStatus() {
  const queryClient = useQueryClient();
  return useMutation<Goal, Error, { goalId: number; status: Goal["status"] }>({
    mutationFn: ({ goalId, status }) =>
      api.patch<Goal>(`/api/v1/goals/${goalId}/status`, { status }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["goals"] }),
  });
}

export function useGoalSuggest() {
  return useMutation<SuggestionResponse, Error, number>({
    mutationFn: (goalId) => api.get<SuggestionResponse>(`/api/v1/goals/${goalId}/suggest`),
  });
}

export function useGoalApply() {
  const queryClient = useQueryClient();
  return useMutation<{ updated: number }, Error, { goalId: number; data: ApplySuggestionRequest }>({
    mutationFn: ({ goalId, data }) =>
      api.post<{ updated: number }>(`/api/v1/goals/${goalId}/apply`, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["goals"] }),
  });
}

// ── Todos ────────────────────────────────────────────────────────────────────

export function useToggleTodo() {
  const queryClient = useQueryClient();
  return useMutation<unknown, Error, { todoId: number; isDone: boolean }>({
    mutationFn: ({ todoId, isDone }) =>
      api.patch(`/api/v1/todos/${todoId}/${isDone ? "done" : "undone"}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["goals"] }),
  });
}

export function useCreateTodo() {
  const queryClient = useQueryClient();
  return useMutation<Todo, Error, CreateTodoRequest>({
    mutationFn: (body) => api.post<Todo>("/api/v1/todos", body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["goals"] }),
  });
}

export function useUpdateTodo() {
  const queryClient = useQueryClient();
  return useMutation<Todo, Error, { todoId: number; data: UpdateTodoRequest }>({
    mutationFn: ({ todoId, data }) => api.patch<Todo>(`/api/v1/todos/${todoId}`, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["goals"] }),
  });
}

export function useDeleteTodo() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, number>({
    mutationFn: (todoId) => api.delete(`/api/v1/todos/${todoId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["goals"] }),
  });
}

// ── Milestones ───────────────────────────────────────────────────────────────

export function useUpdateMilestone() {
  const queryClient = useQueryClient();
  return useMutation<unknown, Error, { milestoneId: number; data: UpdateMilestoneRequest }>({
    mutationFn: ({ milestoneId, data }) =>
      api.patch(`/api/v1/milestones/${milestoneId}`, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["goals"] }),
  });
}

// ── Reschedule ───────────────────────────────────────────────────────────────

export function useReschedulePreview() {
  return useMutation<RescheduleItem[], Error, void>({
    mutationFn: () => api.post<RescheduleItem[]>("/api/v1/reschedule/preview"),
  });
}

export function useRescheduleApply() {
  const queryClient = useQueryClient();
  return useMutation<{ updated: number }, Error, void>({
    mutationFn: () => api.post<{ updated: number }>("/api/v1/reschedule/apply"),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["goals"] }),
  });
}
