"use client";

import Link from "next/link";

import type { Citation } from "@/types/api";

export function CitationDrawer({ citation }: { citation?: Citation | null }) {
  return (
    <aside className="panel min-h-[320px] p-5">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
        Source Focus
      </p>
      {citation ? (
        <div className="mt-4 space-y-4">
          <div>
            <p className="text-sm font-medium text-slate-900">{citation.source}</p>
            <p className="text-sm text-slate-500">
              Page {citation.page} • Chunk {citation.chunk_id}
            </p>
          </div>
          <p className="rounded-2xl bg-slate-50 p-4 text-sm leading-6 text-slate-700">
            {citation.excerpt}
          </p>
          {citation.document_id ? (
            <Link
              href={`/documents/${citation.document_id}`}
              className="inline-flex rounded-xl bg-ink px-4 py-2 text-sm text-white"
            >
              Open document detail
            </Link>
          ) : null}
        </div>
      ) : (
        <p className="mt-4 text-sm text-slate-500">
          Click any citation from a response to inspect the underlying passage.
        </p>
      )}
    </aside>
  );
}
