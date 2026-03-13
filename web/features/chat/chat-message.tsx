"use client";

import { Bot, ShieldCheck, User2 } from "lucide-react";

import { StatusBadge } from "@/components/status-badge";
import type { Citation, ChatMessage as ChatMessageType } from "@/types/api";

export function ChatMessage({
  message,
  citations = [],
  onSelectCitation
}: {
  message: ChatMessageType;
  citations?: Citation[];
  onSelectCitation?: (citation: Citation) => void;
}) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-3xl rounded-[28px] border px-5 py-4 shadow-2xl ${
          isUser
            ? "border-[color:rgba(59,130,246,0.22)] bg-[linear-gradient(135deg,#3B82F6,#6366F1)] text-white"
            : "border-[var(--border-color)] bg-[var(--bg-elevated)] text-[var(--text-primary)] backdrop-blur-xl"
        }`}
      >
        <div className="flex items-center gap-3">
          <div
            className={`flex h-10 w-10 items-center justify-center rounded-2xl ${
              isUser ? "bg-white/15" : "bg-[color:rgba(59,130,246,0.12)] text-[var(--primary)]"
            }`}
          >
            {isUser ? <User2 className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
          </div>
          <div className="flex items-center gap-2">
            <p className={`text-sm font-semibold ${isUser ? "text-white" : "text-[var(--text-primary)]"}`}>
              {isUser ? "You" : "Assistant"}
            </p>
            {!isUser && message.confidence != null ? (
              <StatusBadge
                label={`${Math.round(message.confidence * 100)}% confidence`}
                tone="ready"
                subtle
              />
            ) : null}
            {!isUser && message.refusal ? <StatusBadge label="refusal" tone="error" subtle /> : null}
          </div>
        </div>
        <p className={`mt-4 whitespace-pre-wrap text-sm leading-7 ${isUser ? "text-white/95" : "text-[var(--text-secondary)]"}`}>
          {message.content}
        </p>
        {!isUser && citations.length ? (
          <div className="mt-4 flex flex-wrap gap-2">
            {citations.map((citation) => (
              <button
                key={citation.id}
                onClick={() => onSelectCitation?.(citation)}
                className="inline-flex items-center gap-2 rounded-full border border-[var(--border-color)] bg-[var(--surface-soft)] px-3 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-[var(--text-secondary)] transition hover:border-[color:rgba(59,130,246,0.28)] hover:text-[var(--primary)]"
              >
                <ShieldCheck className="h-3.5 w-3.5" />
                {citation.chunk_id} • p{citation.page}
              </button>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}
