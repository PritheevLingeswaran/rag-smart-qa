"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { UploadDropzone } from "@/features/upload/upload-dropzone";

export default function DashboardPage() {
  const dashboardQuery = useQuery({ queryKey: ["dashboard"], queryFn: api.dashboard });

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Workspace"
        title="Operations dashboard"
        description="Track indexing health, recent uploads, and the current state of your document-grounded assistant."
      />
      <div className="grid gap-4 md:grid-cols-3">
        <StatCard
          label="Documents"
          value={dashboardQuery.data?.stats.total_documents ?? 0}
          subtext="Indexed knowledge sources in this workspace"
        />
        <StatCard
          label="Chunks"
          value={dashboardQuery.data?.stats.total_chunks ?? 0}
          subtext="Chunked passages powering retrieval"
        />
        <StatCard
          label="Chats"
          value={dashboardQuery.data?.stats.total_sessions ?? 0}
          subtext="Persisted conversation sessions"
        />
      </div>
      <div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="panel p-5">
          <h3 className="text-lg font-semibold text-slate-950">Recent indexing activity</h3>
          <div className="mt-4 space-y-3">
            {dashboardQuery.data?.recent_documents.map((document) => (
              <div key={document.id} className="panel-muted flex items-center justify-between p-4">
                <div>
                  <p className="font-medium text-slate-900">{document.filename}</p>
                  <p className="text-sm text-slate-500">
                    {document.chunks_created} chunks • {document.pages} pages
                  </p>
                </div>
                <span className="rounded-full bg-white px-3 py-1 text-xs font-medium text-slate-700">
                  {document.indexing_status}
                </span>
              </div>
            ))}
          </div>
        </div>
        <UploadDropzone />
      </div>
    </div>
  );
}
