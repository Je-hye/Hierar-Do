import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { WeekDetail } from '@/components/WeekDetail';
import { renderWithClient } from '@/lib/test-utils';
import React from 'react';

const mockToggleTodo = vi.fn();
const mockUpdateTodo = vi.fn();
const mockDeleteTodo = vi.fn();
const mockCreateTodo = vi.fn();

vi.mock('@/lib/queries', () => ({
  useToggleTodo: vi.fn(() => ({ mutate: mockToggleTodo })),
  useUpdateTodo: vi.fn(() => ({ mutate: mockUpdateTodo })),
  useDeleteTodo: vi.fn(() => ({ mutate: mockDeleteTodo })),
  useCreateTodo: vi.fn(() => ({ 
    mutate: (data: any, options: any) => {
      mockCreateTodo(data);
      options.onSuccess();
    },
    isPending: false 
  })),
}));

describe('WeekDetail', () => {
  const mockTodos = {
    '2026-05-21': [
      { id: 1, milestone_id: 1, title: 'Todo 1', is_done: false, estimated_minutes: 30, due_date: '2026-05-21', suggested_by_ai: false }
    ]
  };
  const mockMilestones = [
    { id: 1, goal_id: 1, title: 'Week 1', week_number: 1, status: 'active', suggested_by_ai: false, todos: [] }
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    window.confirm = vi.fn(() => true);
  });

  it('renders todos correctly', () => {
    renderWithClient(
      <WeekDetail selectedDate="2026-05-21" milestones={mockMilestones} todosByDate={mockTodos as any} />
    );
    expect(screen.getByText('Todo 1')).toBeInTheDocument();
  });

  it('allows toggling todo', () => {
    renderWithClient(
      <WeekDetail selectedDate="2026-05-21" milestones={mockMilestones} todosByDate={mockTodos as any} />
    );
    const checkbox = screen.getByRole('checkbox');
    fireEvent.click(checkbox);
    expect(mockToggleTodo).toHaveBeenCalledWith({ todoId: 1, isDone: true });
  });

  it('allows inline editing todo title', async () => {
    renderWithClient(
      <WeekDetail selectedDate="2026-05-21" milestones={mockMilestones} todosByDate={mockTodos as any} />
    );
    const titleSpan = screen.getByText('Todo 1');
    fireEvent.doubleClick(titleSpan);
    
    const input = screen.getByDisplayValue('Todo 1');
    await userEvent.clear(input);
    await userEvent.type(input, 'Updated Todo{enter}');
    
    expect(mockUpdateTodo).toHaveBeenCalledWith({
      todoId: 1,
      data: { title: 'Updated Todo' }
    });
  });

  it('allows deleting todo', () => {
    renderWithClient(
      <WeekDetail selectedDate="2026-05-21" milestones={mockMilestones} todosByDate={mockTodos as any} />
    );
    const deleteBtn = screen.getByTitle('삭제');
    fireEvent.click(deleteBtn);
    
    expect(window.confirm).toHaveBeenCalled();
    expect(mockDeleteTodo).toHaveBeenCalledWith(1);
  });

  it('allows adding a new todo', async () => {
    renderWithClient(
      <WeekDetail selectedDate="2026-05-21" milestones={mockMilestones} todosByDate={mockTodos as any} />
    );
    
    const addButtons = screen.getAllByTitle('할 일 추가');
    // Just click the first add button
    fireEvent.click(addButtons[0]);
    
    const input = screen.getByPlaceholderText('할 일 입력...');
    await userEvent.type(input, 'New Todo');
    
    const submitBtn = screen.getByText('추가');
    fireEvent.click(submitBtn);
    
    expect(mockCreateTodo).toHaveBeenCalled();
  });
});
