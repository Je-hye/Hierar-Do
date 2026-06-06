import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useCreateGoal, useToggleTodo } from '@/lib/queries';
import { wrapperWithClient } from '@/lib/test-utils';
import { api } from '@/lib/api';

vi.mock('@/lib/api', () => ({
  api: {
    post: vi.fn(),
    patch: vi.fn(),
    get: vi.fn(),
    delete: vi.fn(),
  },
}));

describe('Queries Hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useCreateGoal', () => {
    it('calls api.post and onSuccess callback', async () => {
      (api.post as any).mockResolvedValueOnce({ goal: { id: 1 } });
      const onSuccess = vi.fn();
      
      const { result } = renderHook(() => useCreateGoal(onSuccess), {
        wrapper: wrapperWithClient(),
      });

      result.current.mutate({ raw_input: 'Test', available_hours: { weekday: 2, weekend: 4 } });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.post).toHaveBeenCalledWith('/api/v1/goals', {
        raw_input: 'Test',
        available_hours: { weekday: 2, weekend: 4 }
      });
      expect(onSuccess).toHaveBeenCalled();
    });

    it('handles error correctly', async () => {
      (api.post as any).mockRejectedValueOnce(new Error('API Error'));
      
      const { result } = renderHook(() => useCreateGoal(), {
        wrapper: wrapperWithClient(),
      });

      result.current.mutate({ raw_input: 'Test', available_hours: { weekday: 2, weekend: 4 } });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error?.message).toBe('API Error');
    });
  });

  describe('useToggleTodo', () => {
    it('calls api.patch with correct status', async () => {
      (api.patch as any).mockResolvedValueOnce({});
      
      const { result } = renderHook(() => useToggleTodo(), {
        wrapper: wrapperWithClient(),
      });

      result.current.mutate({ todoId: 123, isDone: true });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(api.patch).toHaveBeenCalledWith('/api/v1/todos/123/done');
      
      result.current.mutate({ todoId: 123, isDone: false });
      
      await waitFor(() => {
        expect(api.patch).toHaveBeenCalledWith('/api/v1/todos/123/undone');
      });
    });
  });
});
