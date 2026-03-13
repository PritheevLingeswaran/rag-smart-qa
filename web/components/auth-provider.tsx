"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

type AuthUser = {
  userId: string;
  displayName: string;
  email: string;
};

type AuthContextValue = {
  user: AuthUser | null;
  isReady: boolean;
  login: (input: { displayName: string; email: string }) => void;
  logout: () => void;
};

const STORAGE_KEY = "rag-smart-qa-auth-user";

const AuthContext = createContext<AuthContextValue>({
  user: null,
  isReady: false,
  login: () => undefined,
  logout: () => undefined
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw) {
      try {
        setUser(JSON.parse(raw) as AuthUser);
      } catch {
        window.localStorage.removeItem(STORAGE_KEY);
      }
    }
    setIsReady(true);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isReady,
      login: ({ displayName, email }) => {
        const normalizedName = displayName.trim() || email.split("@")[0] || "Workspace User";
        const normalizedEmail = email.trim().toLowerCase();
        const userId = normalizedEmail
          ? normalizedEmail.replace(/[^a-z0-9]+/g, "-")
          : normalizedName.toLowerCase().replace(/[^a-z0-9]+/g, "-");
        const nextUser = { userId, displayName: normalizedName, email: normalizedEmail };
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(nextUser));
        setUser(nextUser);
      },
      logout: () => {
        window.localStorage.removeItem(STORAGE_KEY);
        setUser(null);
      }
    }),
    [isReady, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
