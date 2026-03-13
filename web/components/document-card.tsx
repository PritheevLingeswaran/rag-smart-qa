import { CalendarDays, FileText, Layers3 } from "lucide-react";
import Link from "next/link";

import { StatusBadge } from "@/components/status-badge";
import type { DocumentItem } from "@/types/api";

export function DocumentCard({
  document,
  onDelete,
  onReindex
}: {
  document: DocumentItem;
  onDelete?: (id: string) => void;
  onReindex?: (id: string) => void;
}) {
  return (
    <div className="panel panel-hover p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-4">
          <div className="icon-chip h-14 w-14 rounded-3xl">
            <FileText className="h-5 w-5" />
          </div>
          <div>
            <p className="metric-label">
              {document.file_type}
            </p>
            <Link
              href={`/documents/${document.id}`}
              className="mt-1 block text-lg font-semibold tracking-tight text-[var(--text-primary)] transition hover:text-[var(--primary)]"
            >
              {document.filename}
            </Link>
          </div>
        </div>
        <StatusBadge label={document.indexing_status} tone={document.indexing_status} />
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3">
        <div className="surface-card px-4 py-3">
          <p className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-[var(--text-secondary)]">
            <Layers3 className="h-3.5 w-3.5" />
            Chunks
          </p>
          <p className="mt-2 text-xl font-semibold text-[var(--text-primary)]">{document.chunks_created}</p>
        </div>
        <div className="surface-card px-4 py-3">
          <p className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-[var(--text-secondary)]">
            <CalendarDays className="h-3.5 w-3.5" />
            Uploaded
          </p>
          <p className="mt-2 text-sm font-medium text-[var(--text-primary)]">
            {new Date(document.upload_time).toLocaleDateString()}
          </p>
        </div>
      </div>

      <div className="mt-5 flex items-center justify-between text-sm text-[var(--text-secondary)]">
        <span>{document.pages} pages indexed</span>
        <span>Summary {document.summary_status}</span>
      </div>

      <div className="mt-5 flex gap-2">
        <button
          onClick={() => onReindex?.(document.id)}
          className="btn-secondary px-4 py-2.5"
        >
          Reindex
        </button>
        <button
          onClick={() => onDelete?.(document.id)}
          className="rounded-2xl border border-[color:rgba(239,68,68,0.18)] bg-[color:rgba(239,68,68,0.08)] px-4 py-2.5 text-sm font-medium text-[var(--error)] transition hover:bg-[color:rgba(239,68,68,0.12)]"
        >
          Remove
        </button>
      </div>
    </div>
  );
}
