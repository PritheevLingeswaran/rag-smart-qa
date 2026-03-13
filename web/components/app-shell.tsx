"use client";

import { useQuery } from "@tanstack/react-query";
import { BookOpen, Database, MessageSquareText, Settings2, Sparkles } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/", label: "Dashboard", icon: Sparkles },
  { href: "/chat", label: "Chat", icon: MessageSquareText },
  { href: "/knowledge-base", label: "Knowledge Base", icon: Database },
  { href: "/summaries", label: "Summaries", icon: BookOpen },
  { href: "/settings", label: "Settings", icon: Settings2 }
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const sessionsQuery = useQuery({
    queryKey: ["chat-sessions"],
    queryFn: () => api.chatSessions()
  });

  return (
    <div className="min-h-screen bg-hero-glow">
      <div className="mx-auto flex min-h-screen max-w-[1600px] gap-5 p-4 md:p-6">
        <div className="panel fixed inset-x-4 top-4 z-20 flex items-center justify-between px-4 py-3 lg:hidden">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">
              rag-smart-qa
            </p>
            <p className="text-sm font-medium text-slate-900">Workspace</p>
          </div>
          <div className="flex gap-2 overflow-x-auto">
            {nav.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "rounded-full px-3 py-2 text-xs font-medium",
                  pathname === item.href ? "bg-ink text-white" : "bg-slate-100 text-slate-700"
                )}
              >
                {item.label}
              </Link>
            ))}
          </div>
        </div>
        <aside className="panel hidden w-72 shrink-0 flex-col justify-between p-5 lg:flex">
          <div className="space-y-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">
                rag-smart-qa
              </p>
              <h1 className="mt-2 text-2xl font-semibold">Knowledge copilots for your docs</h1>
            </div>
            <nav className="space-y-2">
              {nav.map((item) => {
                const Icon = item.icon;
                const active = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "flex items-center gap-3 rounded-2xl px-4 py-3 text-sm transition",
                      active
                        ? "bg-ink text-white"
                        : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                    )}
                  >
                    <Icon className="h-4 w-4" />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </nav>
            <div className="panel-muted p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                Recent Chats
              </p>
              <div className="mt-3 space-y-2">
                {sessionsQuery.data?.sessions.slice(0, 5).map((session) => (
                  <Link
                    key={session.id}
                    href={`/chat?session=${session.id}`}
                    className="block rounded-xl px-3 py-2 text-sm text-slate-600 transition hover:bg-white hover:text-slate-900"
                  >
                    {session.title}
                  </Link>
                ))}
                {!sessionsQuery.data?.sessions.length ? (
                  <p className="text-sm text-slate-500">No conversations yet.</p>
                ) : null}
              </div>
            </div>
          </div>
          <div className="rounded-2xl bg-ink px-4 py-4 text-sm text-slate-200">
            Typed APIs, persisted chats, indexed citations, and cached summaries are all live in
            this workspace.
          </div>
        </aside>
        <main className="flex-1 pt-20 lg:pt-0">{children}</main>
      </div>
    </div>
  );
}
