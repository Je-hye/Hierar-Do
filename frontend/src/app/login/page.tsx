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
