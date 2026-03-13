"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Clock3, FileText, Files, Gauge, Layers3, MessageSquare, UploadCloud } from "lucide-react";
import Link from "next/link";

import { EmptyState } from "@/components/empty-state";
import { StatusBadge } from "@/components/status-badge";
import { UploadDropzone } from "@/features/upload/upload-dropzone";
import { api } from "@/lib/api";

export function DashboardPageContent() {
  const dashboardQuery = useQuery({ queryKey: ["dashboard"], queryFn: api.dashboard });
  const stats = dashboardQuery.data?.stats;
  const totalDocs = stats?.total_documents ?? 0;
  const totalChats = stats?.total_sessions ?? 0;
  const totalChunks = stats?.total_chunks ?? 0;
  const readyDocs = stats?.indexing_status.ready ?? 0;
  const recentDocuments = dashboardQuery.data?.recent_documents ?? [];

  return (
    <div className="space-y-10">
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
        {[
          {
            label: "Documents",
            value: totalDocs,
            icon: Files,
            tone: "text-blue-300",
            note: totalDocs ? "Knowledge sources loaded" : "Ready for first upload"
          },
          {
            label: "Chunks",
            value: totalChunks,
            icon: Layers3,
            tone: "text-indigo-300",
            note: totalChunks ? "Indexed passage graph is active" : "No chunks indexed yet"
          },
          {
            label: "Chats",
            value: totalChats,
            icon: MessageSquare,
            tone: "text-violet-300",
            note: totalChats ? "Conversation memory available" : "No active sessions"
          },
          {
            label: "Index health",
            value: totalDocs ? `${Math.round((readyDocs / totalDocs) * 100)}%` : "0%",
            icon: Gauge,
            tone: "text-emerald-300",
            note: "Corpus readiness for grounded answers"
          }
        ].map((item) => {
          const Icon = item.icon;
          return (
            <div key={item.label} className="surface-card rounded-[2rem] p-5">
              <div className="mb-6 flex items-start justify-between">
                <div className={`flex h-12 w-12 items-center justify-center rounded-2xl bg-white/5 ${item.tone}`}>
                  <Icon className="h-6 w-6" />
                </div>
                <StatusBadge label={item.label} tone="queued" subtle />
              </div>
              <p className="text-3xl font-black tracking-tight">{item.value}</p>
              <p className="mt-3 text-[13px] leading-6 text-slate-400">{item.note}</p>
            </div>
          );
        })}
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="space-y-6">
          <div className="panel rounded-[2rem] p-8">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <p className="section-eyebrow">Knowledge activity</p>
                <h2 className="mt-3 text-3xl font-black tracking-tight">Recent intelligence flow</h2>
                <p className="mt-3 max-w-2xl text-[13px] leading-7 text-slate-400">
                  Watch ingestion progress, document motion, and readiness signals from one dashboard surface.
                </p>
              </div>
              <Link href="/knowledge-base" className="btn-secondary gap-2">
                Open knowledge base
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>

            <div className="mt-8 space-y-4">
              {recentDocuments.length ? (
                recentDocuments.map((document) => (
                  <div key={document.id} className="surface-card flex flex-wrap items-center justify-between gap-4 rounded-[1.5rem] p-5">
                    <div className="flex items-center gap-4">
                      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-500/10 text-blue-300">
                        <FileText className="h-5 w-5" />
                      </div>
                      <div>
                        <p className="text-[13px] font-bold text-white">{document.filename}</p>
                        <p className="mt-1 text-[13px] text-slate-400">
                          {document.chunks_created} chunks • {document.pages} pages • {document.file_type.toUpperCase()}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <StatusBadge label={document.indexing_status} tone={document.indexing_status} />
                      <div className="flex items-center gap-2 text-[13px] text-slate-500">
                        <Clock3 className="h-4 w-4" />
                        {new Date(document.upload_time).toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <EmptyState
                  icon={<UploadCloud className="h-7 w-7" />}
                  title="No corpus activity yet"
                  description="Upload a document to activate ingestion, chunking, summaries, and grounded chat workflows."
                  action={
                    <Link href="/knowledge-base" className="btn-primary">
                      Upload first source
                    </Link>
                  }
                />
              )}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <UploadDropzone />

          <div className="panel rounded-[2rem] p-6">
            <p className="section-eyebrow">Workspace status</p>
            <div className="mt-6 space-y-4">
              {[
                ["Documents ready", `${readyDocs}/${totalDocs}`],
                ["Chats active", `${totalChats}`],
                ["Chunks loaded", `${totalChunks}`]
              ].map(([label, value]) => (
                <div key={label} className="surface-card flex items-center justify-between rounded-[1.25rem] p-4">
                  <span className="text-[13px] font-bold text-slate-300">{label}</span>
                  <span className="text-base font-black">{value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
