"use client";

import { FileStack, Quote, Sparkles } from "lucide-react";
import Link from "next/link";

import type { Citation } from "@/types/api";
import { StatusBadge } from "@/components/status-badge";

export function CitationDrawer({ citation }: { citation?: Citation | null }) {
  return (
    <aside className="panel panel-glow min-h-[320px] p-5">
      <p className="section-eyebrow">
        Source Focus
      </p>
      {citation ? (
        <div className="mt-4 space-y-4">
          <div className="surface-card rounded-[26px] p-4">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="icon-chip h-11 w-11">
                  <FileStack className="h-4 w-4" />
                </div>
                <div>
                  <p className="text-sm font-medium text-[var(--text-primary)]">{citation.source}</p>
                  <p className="text-sm text-[var(--text-secondary)]">
                    Page {citation.page} • Chunk {citation.chunk_id}
                  </p>
                </div>
              </div>
              <StatusBadge label={`${Math.round(citation.score * 100)}%`} tone="ready" subtle />
            </div>
          </div>
          <div className="rounded-[26px] border border-[var(--border-color)] bg-[var(--surface-soft)] p-5">
            <div className="flex items-center gap-2 text-[var(--primary)]">
              <Quote className="h-4 w-4" />
              <span className="text-xs font-semibold uppercase tracking-[0.18em]">Excerpt</span>
            </div>
            <p className="mt-4 text-sm leading-7 text-[var(--text-secondary)]">
              {citation.excerpt}
            </p>
          </div>
          {citation.document_id ? (
            <Link
              href={`/documents/${citation.document_id}`}
              className="btn-primary gap-2 px-4 py-3"
            >
              Open document detail
              <Sparkles className="h-4 w-4" />
            </Link>
          ) : null}
        </div>
      ) : (
        <div className="mt-5 rounded-[28px] border border-dashed border-[var(--border-color)] bg-[var(--surface-soft)] p-6">
          <div className="icon-chip h-14 w-14 rounded-3xl">
            <Sparkles className="h-5 w-5" />
          </div>
          <p className="mt-5 text-lg font-semibold text-[var(--text-primary)]">Inspect cited evidence here</p>
          <p className="mt-2 text-sm leading-7 text-[var(--text-secondary)]">
            Click any citation from an assistant response to inspect the exact excerpt, source file, and page context in this drawer.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <StatusBadge label="exact chunk id" tone="queued" subtle />
            <StatusBadge label="page reference" tone="queued" subtle />
            <StatusBadge label="source jump" tone="queued" subtle />
          </div>
        </div>
      )}
    </aside>
  );
}
