"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";

import { PageHeader } from "@/components/page-header";
import { api } from "@/lib/api";
import { SummaryCard } from "@/features/summaries/summary-card";

export default function DocumentDetailPage() {
  const params = useParams<{ id: string }>();
  const documentQuery = useQuery({
    queryKey: ["document", params.id],
    queryFn: () => api.document(params.id)
  });

  const document = documentQuery.data;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Document"
        title={document?.filename ?? "Document detail"}
        description="Preview content, inspect chunk boundaries, and review the cached AI summary for this source."
      />
      <SummaryCard summary={document?.summary ?? null} />
      <div className="grid gap-5 xl:grid-cols-[0.95fr_1.05fr]">
        <div className="panel p-5">
          <h3 className="text-lg font-semibold text-slate-950">Preview</h3>
          <div className="mt-4 space-y-4">
            {document?.preview.map((page) => (
              <div key={page.page} className="panel-muted p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                  Page {page.page}
                </p>
                <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-700">
                  {page.text}
                </p>
              </div>
            ))}
          </div>
        </div>
        <div className="panel p-5">
          <h3 className="text-lg font-semibold text-slate-950">Chunks</h3>
          <div className="mt-4 space-y-3">
            {document?.chunks.map((chunk) => (
              <div key={chunk.chunk_id} className="panel-muted p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                  {chunk.chunk_id} • page {chunk.page}
                </p>
                <p className="mt-2 text-sm leading-7 text-slate-700">{chunk.text}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
