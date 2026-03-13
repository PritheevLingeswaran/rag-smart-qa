"use client";

import { FileText, MessageSquareText, Search, Settings2, Sparkles } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import type { ChatSession, DocumentItem } from "@/types/api";

const baseItems = [
  { href: "/workspace", label: "Dashboard", description: "Overview, health, and quick actions", icon: Sparkles },
  { href: "/chat", label: "Chat", description: "Ask grounded questions", icon: MessageSquareText },
  {
    href: "/knowledge-base",
    label: "Knowledge Base",
    description: "Manage uploaded documents",
    icon: FileText
  },
  { href: "/summaries", label: "Summaries", description: "Browse cached briefings", icon: Search },
  { href: "/settings", label: "Settings", description: "Inspect runtime defaults", icon: Settings2 }
];

export function CommandPalette({
  open,
  onClose,
  sessions,
  documents
}: {
  open: boolean;
  onClose: () => void;
  sessions: ChatSession[];
  documents: DocumentItem[];
}) {
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (!open) {
      setQuery("");
    }
  }, [open]);

  const items = useMemo(() => {
    const dynamic = [
      ...sessions.slice(0, 6).map((session) => ({
        href: `/chat?session=${session.id}`,
        label: session.title,
        description: "Recent chat session",
        icon: MessageSquareText
      })),
      ...documents.slice(0, 6).map((document) => ({
        href: `/documents/${document.id}`,
        label: document.filename,
        description: `${document.chunks_created} chunks • ${document.indexing_status}`,
        icon: FileText
      }))
    ];

    const term = query.trim().toLowerCase();
    return [...baseItems, ...dynamic].filter((item) =>
      term ? `${item.label} ${item.description}`.toLowerCase().includes(term) : true
    );
  }, [documents, query, sessions]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        if (open) {
          onClose();
        }
      }
      if (event.key === "Escape" && open) {
        onClose();
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose, open]);

  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-slate-950/70 px-4 py-[12vh] backdrop-blur-md">
      <div className="w-full max-w-2xl rounded-[32px] border border-white/10 bg-slate-950/95 shadow-[0_40px_120px_rgba(15,23,42,0.55)]">
        <div className="flex items-center gap-3 border-b border-white/10 px-5 py-4">
          <Search className="h-4 w-4 text-cyan-200" />
          <input
            autoFocus
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search pages, documents, and recent chats..."
            className="w-full bg-transparent text-sm text-white outline-none placeholder:text-slate-500"
          />
          <button
            onClick={onClose}
            className="rounded-full border border-white/10 px-3 py-1 text-xs uppercase tracking-[0.18em] text-slate-400 transition hover:border-cyan-400/30 hover:text-cyan-100"
          >
            esc
          </button>
        </div>
        <div className="max-h-[60vh] overflow-y-auto p-3">
          {items.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={`${item.href}-${item.label}`}
                href={item.href}
                onClick={onClose}
                className="flex items-center gap-4 rounded-3xl px-4 py-4 transition hover:bg-white/6"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-cyan-200">
                  <Icon className="h-4 w-4" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-white">{item.label}</p>
                  <p className="mt-1 text-sm text-slate-400">{item.description}</p>
                </div>
              </Link>
            );
          })}
          {!items.length ? (
            <div className="px-5 py-10 text-center text-sm text-slate-400">
              No matching items in the workspace yet.
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
