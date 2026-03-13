"use client";

import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  Bot,
  BrainCircuit,
  Database,
  FilePlus2,
  Gauge,
  Layers3,
  MessageSquareText,
  ShieldCheck
} from "lucide-react";
import Link from "next/link";

import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { StatusBadge } from "@/components/status-badge";
import { UploadDropzone } from "@/features/upload/upload-dropzone";
import { api } from "@/lib/api";

export function DashboardPageContent() {
  const dashboardQuery = useQuery({ queryKey: ["dashboard"], queryFn: api.dashboard });
  const settingsQuery = useQuery({ queryKey: ["settings"], queryFn: api.settings });
  const stats = dashboardQuery.data?.stats;
  const totalDocs = stats?.total_documents ?? 0;
  const totalChats = stats?.total_sessions ?? 0;
  const totalChunks = stats?.total_chunks ?? 0;
  const readyDocs = stats?.indexing_status.ready ?? 0;
  const summaryEnabled = settingsQuery.data?.summaries_enabled ?? false;
  const retrievalMode = settingsQuery.data?.default_retrieval_mode ?? "hybrid_rrf";

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Workspace Overview"
        title="Your document intelligence command center"
        description="Monitor ingestion health, jump into grounded chat, and keep your knowledge base ready for trustworthy answers."
        kicker={
          <div className="flex flex-wrap gap-2">
            <StatusBadge label={`${readyDocs}/${totalDocs} indexed`} tone={readyDocs ? "ready" : "queued"} />
            <StatusBadge label={retrievalMode.replace(/_/g, " ")} tone="queued" />
            <StatusBadge label={summaryEnabled ? "summaries enabled" : "summaries off"} tone={summaryEnabled ? "ready" : "disabled"} />
          </div>
        }
        actions={
          <div className="flex flex-wrap gap-3">
            <Link href="/knowledge-base" className="btn-primary">
              Upload documents
            </Link>
            <Link href="/chat" className="btn-secondary">
              Open chat
            </Link>
          </div>
        }
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-12">
        <StatCard
          className="xl:col-span-3"
          label="Documents"
          value={totalDocs}
          subtext="Managed source files ready for retrieval and citation grounding."
          icon={<Database className="h-5 w-5" />}
          trend={totalDocs ? "Corpus is active" : "Ready for first upload"}
        />
        <StatCard
          className="xl:col-span-3"
          label="Chunks"
          value={totalChunks}
          subtext="Indexed passages powering dense, lexical, and hybrid search."
          icon={<Layers3 className="h-5 w-5" />}
          trend={totalChunks ? "Retrieval context loaded" : "No chunks indexed yet"}
        />
        <StatCard
          className="xl:col-span-3"
          label="Chats"
          value={totalChats}
          subtext="Saved chat sessions with source-backed answers and follow-ups."
          icon={<MessageSquareText className="h-5 w-5" />}
          trend={totalChats ? "Conversation history available" : "No active sessions"}
        />
        <div className="panel panel-hover premium-border p-5 xl:col-span-3">
          <div className="flex items-start justify-between">
            <div>
              <p className="metric-label">Index health</p>
              <p className="mt-4 text-4xl font-semibold tracking-tight text-[var(--text-primary)]">
                {totalDocs ? `${Math.round((readyDocs / totalDocs) * 100)}%` : "0%"}
              </p>
            </div>
            <div className="icon-chip">
              <ShieldCheck className="h-5 w-5" />
            </div>
          </div>
          <p className="mt-4 text-sm leading-7 text-[var(--text-secondary)]">
            Tracks how much of the corpus is ingestion-complete and ready for confident answers.
          </p>
          <div className="mt-4 h-2 rounded-full bg-[var(--surface-soft)]">
            <div
              className="h-2 rounded-full bg-[linear-gradient(135deg,#3B82F6,#6366F1,#8B5CF6)]"
              style={{ width: `${totalDocs ? Math.max(8, (readyDocs / totalDocs) * 100) : 8}%` }}
            />
          </div>
        </div>
      </div>

      <div className="grid gap-5 xl:grid-cols-12">
        <div className="space-y-5 xl:col-span-8">
          <div className="panel premium-border p-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <p className="section-eyebrow">Mission control</p>
                <h3 className="mt-2 text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
                  System status and recent activity
                </h3>
                <p className="mt-2 max-w-2xl text-sm leading-7 text-[var(--text-secondary)]">
                  Keep an eye on ingestion readiness, summary cache posture, and the documents entering the knowledge base.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <StatusBadge label={summaryEnabled ? "summary cache active" : "summary cache off"} tone={summaryEnabled ? "ready" : "disabled"} />
                <StatusBadge label={`retrieval ${retrievalMode.replace(/_/g, " ")}`} tone="queued" />
              </div>
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-3">
              {[
                ["Ready documents", readyDocs, "Documents with completed indexing state.", Gauge],
                ["Summary cache", summaryEnabled ? "Active" : "Off", "Generated briefings ready to load instantly.", BrainCircuit],
                ["Retrieval default", retrievalMode, "Current default mode exposed by the backend.", Bot]
              ].map(([label, value, body, Icon]) => {
                const ItemIcon = Icon as typeof Gauge;
                return (
                  <div key={label as string} className="surface-card p-5">
                    <div className="icon-chip">
                      <ItemIcon className="h-4 w-4" />
                    </div>
                    <p className="metric-label mt-4">{label as string}</p>
                    <p className="mt-3 text-3xl font-semibold text-[var(--text-primary)]">{value as string | number}</p>
                    <p className="mt-2 text-sm text-[var(--text-secondary)]">{body as string}</p>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="panel p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="section-eyebrow">Activity stream</p>
                <h3 className="mt-2 text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
                  Recent document activity
                </h3>
              </div>
              <Link href="/knowledge-base" className="btn-secondary inline-flex items-center gap-2">
                Open knowledge base
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>

            <div className="mt-5 space-y-3">
              {dashboardQuery.data?.recent_documents.length ? (
                dashboardQuery.data.recent_documents.map((document) => (
                  <div key={document.id} className="surface-card flex flex-wrap items-center justify-between gap-4 p-4">
                    <div>
                      <p className="text-base font-semibold text-[var(--text-primary)]">{document.filename}</p>
                      <p className="mt-1 text-sm text-[var(--text-secondary)]">
                        {document.chunks_created} chunks • {document.pages} pages • {document.file_type.toUpperCase()}
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <StatusBadge label={document.indexing_status} tone={document.indexing_status} />
                      <span className="text-sm text-[var(--text-secondary)]">
                        {new Date(document.upload_time).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                ))
              ) : (
                <EmptyState
                  icon={<FilePlus2 className="h-7 w-7" />}
                  title="Start by ingesting your first source"
                  description="Upload PDFs, markdown notes, HTML, or plain text and this activity stream becomes your workspace timeline immediately."
                  action={
                    <Link href="/knowledge-base" className="btn-primary">
                      Go to knowledge base
                    </Link>
                  }
                  secondary="Metrics, summaries, and grounded chat will light up as soon as the first document lands."
                />
              )}
            </div>
          </div>
        </div>

        <div className="space-y-5 xl:col-span-4">
          <UploadDropzone />

          <div className="panel p-6">
            <p className="section-eyebrow">Quick actions</p>
            <div className="mt-4 space-y-3">
              {[
                {
                  href: "/chat",
                  label: "Launch AI chat",
                  description: "Ask follow-up questions with source citations.",
                  icon: Bot
                },
                {
                  href: "/summaries",
                  label: "Review summaries",
                  description: "Browse briefings and key insights before chatting.",
                  icon: BrainCircuit
                },
                {
                  href: "/settings",
                  label: "Inspect settings",
                  description: "Review models, feature flags, and environment details.",
                  icon: ShieldCheck
                }
              ].map((item) => {
                const Icon = item.icon;
                return (
                  <Link key={item.href} href={item.href} className="surface-card flex items-center gap-4 p-4 transition hover:border-[color:rgba(59,130,246,0.3)]">
                    <div className="icon-chip">
                      <Icon className="h-4 w-4" />
                    </div>
                    <div>
                      <p className="font-semibold text-[var(--text-primary)]">{item.label}</p>
                      <p className="mt-1 text-sm text-[var(--text-secondary)]">{item.description}</p>
                    </div>
                  </Link>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
