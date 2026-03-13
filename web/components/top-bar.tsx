"use client";

import { Command, MoonStar, Search, SunMedium } from "lucide-react";

import { useTheme } from "@/components/theme-provider";

export function TopBar({
  title,
  subtitle,
  onOpenPalette
}: {
  title: string;
  subtitle: string;
  onOpenPalette: () => void;
}) {
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="sticky top-0 z-20 mb-6 flex items-center justify-between rounded-[30px] border border-[var(--border-color)] bg-[color:rgba(255,255,255,0.82)] px-5 py-4 backdrop-blur-xl dark:bg-[color:rgba(15,23,42,0.78)]">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-[var(--primary)]">
          rag-smart-qa workspace
        </p>
        <h1 className="mt-2 text-xl font-semibold tracking-tight text-[var(--text-primary)]">{title}</h1>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">{subtitle}</p>
      </div>
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenPalette}
          className="hidden items-center gap-3 rounded-2xl border border-[var(--border-color)] bg-[var(--surface-soft)] px-4 py-3 text-sm text-[var(--text-secondary)] transition hover:border-[color:rgba(59,130,246,0.3)] hover:text-[var(--text-primary)] md:flex"
        >
          <Search className="h-4 w-4" />
          Search workspace
          <span className="inline-flex items-center gap-1 rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] px-2 py-1 text-[11px] uppercase tracking-[0.18em] text-[var(--text-secondary)]">
            <Command className="h-3 w-3" />K
          </span>
        </button>
        <button
          onClick={toggleTheme}
          className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-[var(--border-color)] bg-[var(--surface-soft)] text-[var(--text-secondary)] transition hover:border-[color:rgba(59,130,246,0.3)] hover:text-[var(--primary)]"
          aria-label="Toggle theme"
        >
          {theme === "dark" ? <SunMedium className="h-4 w-4" /> : <MoonStar className="h-4 w-4" />}
        </button>
      </div>
    </div>
  );
}
