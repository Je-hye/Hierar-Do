"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email || !password || !confirmPassword) return;

    if (password !== confirmPassword) {
      setError("비밀번호가 일치하지 않습니다.");
      return;
    }
    
    setError(null);
    setIsLoading(true);

    try {
      // 회원가입 API 호출
      await api.post("/api/v1/auth/register", { email, password });
      
      // 회원가입 성공 시 바로 로그인 페이지로 이동하거나 자동 로그인 처리
      // 편의상 자동 로그인 처리
      await api.post("/api/v1/auth/login", { email, password });
      
      router.push("/");
      router.refresh();
    } catch (err: any) {
      setError(err.message || "회원가입에 실패했습니다.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface px-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-lg p-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-extrabold text-primary mb-2">Hierar-Do</h1>
          <p className="text-on-surface-variant text-sm">새로운 계정을 생성하세요</p>
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
              minLength={6}
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-on-surface mb-1.5">
              비밀번호 확인
            </label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-4 py-3 rounded-xl border border-outline-variant focus:outline-none focus:ring-2 focus:ring-primary transition-all text-sm"
              placeholder="비밀번호를 한 번 더 입력하세요"
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
            disabled={isLoading || !email || !password || !confirmPassword}
            className="w-full bg-primary text-white py-3.5 rounded-xl font-bold hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed mt-2"
          >
            {isLoading ? "가입 중..." : "회원가입"}
          </button>
        </form>

        <div className="mt-8 text-center text-sm text-on-surface-variant">
          이미 계정이 있으신가요?{" "}
          <Link href="/login" className="text-primary font-bold hover:underline">
            로그인
          </Link>
        </div>
      </div>
    </div>
  );
}
