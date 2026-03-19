"use client";

import { createContext, useContext, useEffect, useState } from "react";

type Theme = "light" | "dark";

interface ThemeContextValue {
  theme: Theme;
  toggleTheme: () => void;
  setTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeContextValue>({
  theme: "dark",
  toggleTheme: () => {},
  setTheme: () => {},
});

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>("dark");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("theme") as Theme | null;
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const initial = stored || (prefersDark ? "dark" : "light");
    setThemeState(initial);
    document.documentElement.setAttribute("data-theme", initial);
    setMounted(true);
  }, []);

  const setTheme = (t: Theme) => {
    setThemeState(t);
    document.documentElement.setAttribute("data-theme", t);
    localStorage.setItem("theme", t);
  };

  const toggleTheme = () => setTheme(theme === "dark" ? "light" : "dark");

  if (!mounted) {
    return (
      <div
        style={{ visibility: "hidden" }}
        data-theme="dark"
        suppressHydrationWarning
      >
        {children}
      </div>
    );
  }

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}
