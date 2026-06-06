import '@testing-library/jest-dom';
import { cleanup } from '@testing-library/react';
import { afterEach, vi } from 'vitest';

afterEach(() => {
  cleanup();
});

// fetch 모킹 (Next.js/TanStack Query 테스트용)
global.fetch = vi.fn();
