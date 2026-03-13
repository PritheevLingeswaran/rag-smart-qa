"use client";

import { cn } from "@/lib/utils";

const tones: Record<string, string> = {
  ready: "bg-emerald-500/12 text-emerald-600 ring-1 ring-inset ring-emerald-500/22 dark:text-emerald-200",
  processing: "bg-amber-400/12 text-amber-600 ring-1 ring-inset ring-amber-400/22 dark:text-amber-100",
  queued: "bg-sky-400/12 text-sky-600 ring-1 ring-inset ring-sky-400/22 dark:text-sky-100",
  failed: "bg-rose-500/12 text-rose-600 ring-1 ring-inset ring-rose-500/22 dark:text-rose-100",
  success: "bg-emerald-500/12 text-emerald-600 ring-1 ring-inset ring-emerald-500/22 dark:text-emerald-200",
  error: "bg-rose-500/12 text-rose-600 ring-1 ring-inset ring-rose-500/22 dark:text-rose-100",
  disabled: "bg-[var(--surface-soft)] text-[var(--text-secondary)] ring-1 ring-inset ring-[var(--border-color)]",
  default: "bg-[var(--surface-soft)] text-[var(--text-secondary)] ring-1 ring-inset ring-[var(--border-color)]"
};

export function StatusBadge({
  label,
  tone,
  subtle = false
}: {
  label: string;
  tone?: string;
  subtle?: boolean;
}) {
  const key = tone?.toLowerCase() ?? "default";

  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em]",
        tones[key] ?? tones.default,
        subtle && "bg-[var(--surface-soft)] text-[var(--text-secondary)] ring-[var(--border-color)]"
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {label}
    </span>
  );
}
