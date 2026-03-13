"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import type { Citation } from "@/types/api";
import { CitationDrawer } from "@/features/chat/citation-drawer";

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
      await queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
      await queryClient.invalidateQueries({ queryKey: ["chat-session", data.session_id] });
    }
  });

  const messages = sessionQuery.data?.messages ?? [];
  const lastResponse = mutation.data;

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
      <section className="panel flex min-h-[780px] flex-col p-5">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Chat</p>
            <h3 className="mt-1 text-2xl font-semibold text-slate-950">Grounded workspace chat</h3>
          </div>
          <div className="flex items-center gap-2">
            <select
              className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
              value={retrievalMode}
              onChange={(event) => setRetrievalMode(event.target.value as (typeof retrievalModes)[number])}
            >
              {retrievalModes.map((mode) => (
                <option key={mode} value={mode}>
                  {mode}
                </option>
              ))}
            </select>
            <button
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm"
              onClick={() => setSessionId(undefined)}
            >
              New chat
            </button>
          </div>
        </div>

        <div className="mt-6 flex-1 space-y-4 overflow-y-auto">
          {!messages.length && !lastResponse ? (
            <div className="flex h-full items-center justify-center rounded-3xl border border-dashed border-slate-200 bg-slate-50 text-center text-slate-500">
              <div>
                <p className="text-lg font-medium text-slate-900">Ask about your indexed knowledge base</p>
                <p className="mt-2 max-w-md text-sm">
                  Responses include citations, confidence, and refusal handling when the corpus does not support an answer.
                </p>
              </div>
            </div>
          ) : null}

          {messages.map((item) => (
            <div
              key={item.id}
              className={item.role === "user" ? "ml-auto max-w-2xl rounded-3xl bg-ink px-5 py-4 text-white" : "mr-auto max-w-3xl rounded-3xl bg-slate-100 px-5 py-4 text-slate-900"}
            >
              <p className="text-sm leading-7">{item.content}</p>
            </div>
          ))}

          {lastResponse ? (
            <div className="space-y-3 rounded-3xl bg-white p-5 shadow-panel">
              <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
                <span>Confidence {Math.round(lastResponse.confidence * 100)}%</span>
                <span>Refusal {String(lastResponse.refusal.is_refusal)}</span>
              </div>
              <p className="text-sm leading-7 text-slate-900">{lastResponse.answer}</p>
              <div className="flex flex-wrap gap-2">
                {lastResponse.citations.map((citation) => (
                  <button
                    key={citation.id}
                    className="rounded-full bg-slate-100 px-3 py-2 text-xs font-medium text-slate-700"
                    onClick={() => setActiveCitation(citation)}
                  >
                    {citation.chunk_id} • page {citation.page}
                  </button>
                ))}
              </div>
            </div>
          ) : null}
        </div>

        <div className="mt-6 rounded-3xl border border-slate-200 bg-white p-4">
          <textarea
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            rows={4}
            placeholder="Ask a question about the uploaded documents..."
            className="w-full resize-none border-0 bg-transparent text-sm outline-none"
          />
          <div className="mt-3 flex items-center justify-between">
            <p className="text-xs text-slate-500">
              Same-session follow-ups stay attached to the active workspace chat.
            </p>
            <button
              className="rounded-2xl bg-ink px-4 py-2 text-sm text-white disabled:opacity-40"
              disabled={!message.trim() || mutation.isPending}
              onClick={() => mutation.mutate()}
            >
              {mutation.isPending ? "Thinking..." : "Send"}
            </button>
          </div>
        </div>
      </section>
      <CitationDrawer citation={activeCitation} />
    </div>
  );
}
