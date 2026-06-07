"use client";
import React, { createContext, useContext, useEffect, useState } from "react";
import { UserOut } from "./types";
import { api } from "./api";

interface AuthContextType {
  user: UserOut | null;
  isLoading: boolean;
  login: (user: UserOut) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // 앱 로드 시 현재 로그인된 유저 정보 가져오기
    api.get<UserOut>("/api/v1/auth/me")
      .then((data) => {
        setUser(data);
      })
      .catch(() => {
        setUser(null);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, []);

  const login = (userData: UserOut) => setUser(userData);
  
  const logout = async () => {
    try {
      await api.post("/api/v1/auth/logout", {});
    } catch (e) {
      console.error("Logout failed", e);
    }
    setUser(null);
    window.location.href = "/login";
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
