import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { GoalModal } from '@/components/GoalModal';
import { renderWithClient } from '@/lib/test-utils';
import React from 'react';

// Mock the queries
const mockCreateGoal = vi.fn();
vi.mock('@/lib/queries', () => ({
  useCreateGoal: vi.fn((onClose) => ({
    mutate: (data: any, options: any) => mockCreateGoal(data, options, onClose),
    isPending: false,
  })),
}));

describe('GoalModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders correctly', () => {
    const onClose = vi.fn();
    renderWithClient(<GoalModal onClose={onClose} />);
    expect(screen.getByText('새 목표 만들기')).toBeInTheDocument();
  });

  it('submits form successfully', async () => {
    mockCreateGoal.mockImplementation((data, options, onClose) => {
      onClose(); // simulate success
    });

    const onClose = vi.fn();
    renderWithClient(<GoalModal onClose={onClose} />);
    
    const input = screen.getByPlaceholderText(/토익 900점 받고 싶어/);
    await userEvent.type(input, 'Test Goal');
    
    const submitBtn = screen.getByText('목표 생성');
    fireEvent.click(submitBtn);
    
    expect(mockCreateGoal).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });

  it('shows error message on failure', async () => {
    mockCreateGoal.mockImplementation((data, options, onClose) => {
      options.onError(new Error('Test error message'));
    });

    const onClose = vi.fn();
    renderWithClient(<GoalModal onClose={onClose} />);
    
    const input = screen.getByPlaceholderText(/토익 900점 받고 싶어/);
    await userEvent.type(input, 'Fail Goal');
    
    const submitBtn = screen.getByText('목표 생성');
    fireEvent.click(submitBtn);
    
    await waitFor(() => {
      expect(screen.getByText('Test error message')).toBeInTheDocument();
    });
    expect(onClose).not.toHaveBeenCalled();
  });
});
