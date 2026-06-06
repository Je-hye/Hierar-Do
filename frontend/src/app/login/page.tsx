"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email || !password) return;
    
    setError(null);
    setIsLoading(true);

    try {
      // 1. 로그인 API 호출 (HttpOnly 쿠키 설정됨)
      await api.post("/api/v1/auth/login", { email, password });
      
      // 2. 현재 사용자 정보 가져오기
      const user = await api.get<any>("/api/v1/auth/me");
      login(user);
      
      // 3. 메인 페이지로 이동
      router.push("/");
      router.refresh();
    } catch (err: any) {
      setError(err.message || "로그인에 실패했습니다. 이메일과 비밀번호를 확인해주세요.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface px-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-lg p-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-extrabold text-primary mb-2">Hierar-Do</h1>
          <p className="text-on-surface-variant text-sm">계층적 AI 할 일 관리 시작하기</p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          <div>
            <label className="block text-sm font-semibold text-on-surface mb-1.5">
              이메일
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-3 rounded-xl border border-outline-variant focus:outline-none focus:ring-2 focus:ring-primary transition-all text-sm"
              placeholder="name@example.com"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-on-surface mb-1.5">
              비밀번호
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 rounded-xl border border-outline-variant focus:outline-none focus:ring-2 focus:ring-primary transition-all text-sm"
              placeholder="비밀번호를 입력하세요"
              required
            />
          </div>

          {error && (
            <p className="text-sm text-error bg-red-50 border border-red-100 p-3 rounded-lg text-center">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={isLoading || !email || !password}
            className="w-full bg-primary text-white py-3.5 rounded-xl font-bold hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed mt-2"
          >
            {isLoading ? "로그인 중..." : "로그인"}
          </button>
        </form>

        <div className="relative my-8">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-outline-variant"></div>
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-2 bg-white text-on-surface-variant">또는</span>
          </div>
        </div>

        <a
          href="http://localhost:8000/api/v1/auth/google"
          className="w-full flex items-center justify-center gap-3 bg-white border border-outline-variant text-on-surface py-3.5 rounded-xl font-bold hover:bg-surface-variant/50 transition-colors"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24">
            <path
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              fill="#4285F4"
            />
            <path
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              fill="#34A853"
            />
            <path
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              fill="#FBBC05"
            />
            <path
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              fill="#EA4335"
            />
            <path d="M1 1h22v22H1z" fill="none" />
          </svg>
          Google로 계속하기
        </a>

        <div className="mt-8 text-center text-sm text-on-surface-variant">
          아직 계정이 없으신가요?{" "}
          <Link href="/register" className="text-primary font-bold hover:underline">
            회원가입
          </Link>
        </div>
      </div>
    </div>
  );
}
