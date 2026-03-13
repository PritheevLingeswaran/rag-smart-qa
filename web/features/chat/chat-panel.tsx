"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bot, LoaderCircle, Plus, Sparkles } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { EmptyState } from "@/components/empty-state";
import { StatusBadge } from "@/components/status-badge";
import { useToast } from "@/components/toast-provider";
import { api } from "@/lib/api";
import type { Citation } from "@/types/api";
import { CitationDrawer } from "@/features/chat/citation-drawer";
import { ChatMessage } from "@/features/chat/chat-message";

const retrievalModes = [
  "dense",
  "bm25",
  "hybrid_weighted",
  "hybrid_rrf",
  "hybrid_rrf_rerank"
] as const;

export function ChatPanel() {
  const params = useSearchParams();
  const queryClient = useQueryClient();
  const { pushToast } = useToast();
  const [message, setMessage] = useState("");
  const [retrievalMode, setRetrievalMode] = useState<(typeof retrievalModes)[number]>("hybrid_rrf");
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);
  const [sessionId, setSessionId] = useState<string | undefined>(params.get("session") ?? undefined);

  const sessionQuery = useQuery({
    queryKey: ["chat-session", sessionId],
    queryFn: () => api.chatSession(sessionId!),
    enabled: Boolean(sessionId)
  });

  useEffect(() => {
    setSessionId(params.get("session") ?? undefined);
  }, [params]);

  const mutation = useMutation({
    mutationFn: () =>
      api.chatQuery({
        question: message,
        session_id: sessionId,
        retrieval_mode: retrievalMode,
        top_k: 8
      }),
    onSuccess: async (data) => {
      setMessage("");
      setSessionId(data.session_id);
      pushToast({
        tone: "success",
        title: "Answer generated",
        description: `${data.citations.length} citations attached to the latest response.`
      });
      await queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
      await queryClient.invalidateQueries({ queryKey: ["chat-session", data.session_id] });
    },
    onError: (error) => {
      pushToast({
        tone: "error",
        title: "Chat request failed",
        description: error instanceof Error ? error.message : "Unknown error"
      });
    }
  });

  const messages = sessionQuery.data?.messages ?? [];
  const lastResponse = mutation.data;
  const assistantCitations = lastResponse?.citations ?? [];

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
      <section className="panel panel-glow flex min-h-[780px] flex-col overflow-hidden p-5">
        <div className="flex flex-col gap-4 border-b border-[var(--border-color)] pb-5 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="section-eyebrow">Chat</p>
            <h3 className="mt-1 text-2xl font-semibold tracking-tight text-[var(--text-primary)]">Grounded workspace chat</h3>
            <p className="mt-2 text-sm text-[var(--text-secondary)]">
              Premium answer cards, retrieval controls, and source-backed follow-up workflows.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="rounded-2xl border border-[var(--border-color)] bg-[var(--surface-soft)] p-1">
              <div className="flex flex-wrap gap-1">
                {retrievalModes.map((mode) => (
                  <button
                    key={mode}
                    onClick={() => setRetrievalMode(mode)}
                    className={`rounded-xl px-3 py-2 text-xs font-semibold uppercase tracking-[0.16em] transition ${
                      retrievalMode === mode
                        ? "bg-[linear-gradient(135deg,#3B82F6,#6366F1)] text-white"
                        : "text-[var(--text-secondary)] hover:bg-[var(--bg-primary)] hover:text-[var(--text-primary)]"
                    }`}
                  >
                    {mode.replace(/_/g, " ")}
                  </button>
                ))}
              </div>
            </div>
            <button
              className="btn-secondary inline-flex items-center gap-2"
              onClick={() => setSessionId(undefined)}
            >
              <Plus className="h-4 w-4" />
              New chat
            </button>
          </div>
        </div>

        <div className="mt-6 flex-1 space-y-4 overflow-y-auto pr-1">
          {!messages.length && !lastResponse ? (
            <EmptyState
              icon={<Bot className="h-7 w-7" />}
              title="Ask anything about your workspace documents"
              description="This chat experience is designed to feel like a real AI product even before your first conversation. Choose a retrieval mode, ask a question, and inspect the exact evidence in the source drawer."
              action={
                <button
                  onClick={() =>
                    setMessage("Give me a high-level overview of the documents currently in this workspace.")
                  }
                  className="rounded-2xl bg-white px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-100"
                >
                  Start with a guided prompt
                </button>
              }
              secondary="Citation-backed answers, refusal handling, and workspace memory are ready"
            />
          ) : null}

          {messages.map((item) => (
            <ChatMessage key={item.id} message={item} onSelectCitation={setActiveCitation} />
          ))}

          {lastResponse ? (
            <div className="space-y-4 rounded-[30px] border border-[var(--border-color)] bg-[var(--bg-elevated)] p-5 shadow-2xl backdrop-blur-xl">
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge label={`${Math.round(lastResponse.confidence * 100)}% confidence`} tone="ready" />
                <StatusBadge
                  label={lastResponse.refusal.is_refusal ? "unsupported answer" : "answer generated"}
                  tone={lastResponse.refusal.is_refusal ? "error" : "success"}
                />
                {typeof lastResponse.timing.latency_ms === "number" ? (
                  <StatusBadge
                    label={`${Math.round(Number(lastResponse.timing.latency_ms))} ms`}
                    tone="queued"
                    subtle
                  />
                ) : null}
              </div>
              <p className="text-sm leading-8 text-[var(--text-secondary)]">{lastResponse.answer}</p>
              <div className="flex flex-wrap gap-2">
                {assistantCitations.map((citation) => (
                  <button
                    key={citation.id}
                    className="rounded-full border border-[var(--border-color)] bg-[var(--surface-soft)] px-3 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-[var(--text-secondary)] transition hover:border-[color:rgba(59,130,246,0.28)] hover:text-[var(--primary)]"
                    onClick={() => setActiveCitation(citation)}
                  >
                    {citation.chunk_id} • page {citation.page}
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          {mutation.isPending ? (
            <div className="flex items-center gap-3 rounded-[24px] border border-[color:rgba(59,130,246,0.18)] bg-[color:rgba(59,130,246,0.08)] px-4 py-3 text-sm text-[var(--primary)]">
              <LoaderCircle className="h-4 w-4 animate-spin" />
              Generating a grounded answer and attaching citations...
            </div>
          ) : null}
        </div>

        <div className="sticky bottom-0 mt-6 rounded-[30px] border border-[var(--border-color)] bg-[var(--bg-elevated)] p-4 backdrop-blur-xl">
          <textarea
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            rows={4}
            placeholder="Ask a question about the uploaded documents..."
            className="w-full resize-none border-0 bg-transparent text-sm leading-7 text-[var(--text-primary)] outline-none placeholder:text-[var(--text-muted)]"
          />
          <div className="mt-3 flex items-center justify-between">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge label={retrievalMode} tone="queued" subtle />
              <p className="text-xs text-[var(--text-secondary)]">
                Same-session follow-ups stay attached to the active workspace chat.
              </p>
            </div>
            <button
              className="btn-primary disabled:cursor-not-allowed disabled:opacity-40"
              disabled={!message.trim() || mutation.isPending}
              onClick={() => mutation.mutate()}
            >
              {mutation.isPending ? (
                <span className="inline-flex items-center gap-2">
                  <LoaderCircle className="h-4 w-4 animate-spin" />
                  Thinking
                </span>
              ) : (
                <span className="inline-flex items-center gap-2">
                  <Sparkles className="h-4 w-4" />
                  Send
                </span>
              )}
            </button>
          </div>
        </div>
      </section>
      <CitationDrawer citation={activeCitation} />
    </div>
  );
}
