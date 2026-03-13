"use client";

import { useQuery } from "@tanstack/react-query";
import {
  BookOpen,
  Bot,
  Command,
  Database,
  LogOut,
  MessageSquareText,
  Settings2,
  Sparkles,
  Zap
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { CommandPalette } from "@/components/command-palette";
import { LoadingSkeleton } from "@/components/loading-skeleton";
import { StatusBadge } from "@/components/status-badge";
import { TopBar } from "@/components/top-bar";
import { useToast } from "@/components/toast-provider";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/workspace", label: "Dashboard", icon: Sparkles },
  { href: "/chat", label: "Chat", icon: MessageSquareText },
  { href: "/knowledge-base", label: "Knowledge Base", icon: Database },
  { href: "/summaries", label: "Summaries", icon: BookOpen },
  { href: "/settings", label: "Settings", icon: Settings2 }
];

const publicRoutes = new Set(["/", "/login"]);

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, isReady, logout } = useAuth();
  const { pushToast } = useToast();
  const [paletteOpen, setPaletteOpen] = useState(false);
  const isPublicRoute = publicRoutes.has(pathname);
  const isDocumentsRoute = pathname.startsWith("/documents/");

  const sessionsQuery = useQuery({
    queryKey: ["chat-sessions"],
    queryFn: () => api.chatSessions(),
    enabled: !isPublicRoute
  });
  const documentsQuery = useQuery({
    queryKey: ["documents"],
    queryFn: api.documents,
    enabled: !isPublicRoute
  });

  const heading = useMemo(() => {
    const current = nav.find((item) => item.href === pathname);
    if (current) {
      return current.label;
    }
    if (isDocumentsRoute) {
      return "Document Detail";
    }
    return "Workspace";
  }, [isDocumentsRoute, pathname]);

  const subtitle = useMemo(() => {
    if (pathname === "/chat") {
      return "Grounded answers with citations, retrieval controls, and source inspection.";
    }
    if (pathname === "/knowledge-base") {
      return "Ingest, index, and curate the corpus that powers your assistant.";
    }
    if (pathname === "/summaries") {
      return "Review cached document briefings, insights, and answerability context.";
    }
    if (pathname === "/settings") {
      return "Runtime defaults, model configuration, and workspace feature flags.";
    }
    if (isDocumentsRoute) {
      return "Inspect source metadata, preview content, and review summary outputs in one place.";
    }
    return "A premium AI workspace for document retrieval, summaries, and cited chat.";
  }, [isDocumentsRoute, pathname]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen((current) => !current);
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  useEffect(() => {
    if (!isReady) {
      return;
    }

    if (!user && !isPublicRoute) {
      router.replace("/login");
    }

    if (user && pathname === "/login") {
      router.replace("/workspace");
    }
  }, [isPublicRoute, isReady, pathname, router, user]);

  if (!isReady) {
    return (
      <div className="app-bg-grid flex min-h-screen items-center justify-center p-6">
        <div className="panel panel-glow w-full max-w-lg p-8">
          <LoadingSkeleton className="h-4 w-28" />
          <LoadingSkeleton className="mt-4 h-12 w-3/4" />
          <LoadingSkeleton className="mt-6 h-28 w-full" />
        </div>
      </div>
    );
  }

  if (isPublicRoute) {
    return <>{children}</>;
  }

  if (!user) {
    return null;
  }

  return (
    <div className="app-bg-grid min-h-screen">
      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        sessions={sessionsQuery.data?.sessions ?? []}
        documents={documentsQuery.data?.documents ?? []}
      />

      <div className="mx-auto flex min-h-screen max-w-[1680px] gap-5 p-4 md:p-6">
        <div className="panel fixed inset-x-4 top-4 z-20 flex items-center justify-between px-4 py-3 lg:hidden">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[linear-gradient(135deg,#3B82F6,#6366F1,#8B5CF6)] text-white">
              <Bot className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--primary)]">
                rag-smart-qa
              </p>
              <p className="text-sm font-medium text-[var(--text-primary)]">AI workspace</p>
            </div>
          </div>
          <div className="flex gap-2 overflow-x-auto">
            {nav.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "rounded-full px-3 py-2 text-xs font-medium",
                    active
                      ? "bg-[var(--primary)] text-white"
                      : "bg-[var(--surface-soft)] text-[var(--text-secondary)]"
                  )}
                >
                  {item.label}
                </Link>
              );
            })}
          </div>
        </div>

        <aside className="panel panel-glow hidden w-[320px] shrink-0 flex-col justify-between overflow-hidden p-6 lg:flex">
          <div className="space-y-7">
            <div className="premium-ring rounded-[28px] border border-[var(--border-color)] bg-[linear-gradient(135deg,rgba(59,130,246,0.12),rgba(99,102,241,0.06),rgba(139,92,246,0.12))] p-5">
              <div className="flex items-center gap-4">
                <div className="flex h-14 w-14 items-center justify-center rounded-3xl bg-[linear-gradient(135deg,#3B82F6,#6366F1,#8B5CF6)] text-white shadow-[0_20px_40px_rgba(59,130,246,0.24)]">
                  <Bot className="h-6 w-6" />
                </div>
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-[var(--text-secondary)]">
                    rag-smart-qa
                  </p>
                  <h1 className="mt-1 text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
                    Retrieval workspace
                  </h1>
                </div>
              </div>
              <p className="mt-4 text-sm leading-7 text-[var(--text-secondary)]">
                Premium document-grounded chat, knowledge base controls, and explainable AI answers.
              </p>
              <div className="mt-4 flex items-center gap-2">
                <StatusBadge label="api connected" tone="ready" />
                <StatusBadge label={`${documentsQuery.data?.documents.length ?? 0} docs`} tone="queued" />
              </div>
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
                      "group flex items-center gap-3 rounded-[22px] px-4 py-3.5 text-sm transition",
                      active
                        ? "bg-[linear-gradient(135deg,#3B82F6,#6366F1,#8B5CF6)] text-white shadow-[0_18px_40px_rgba(99,102,241,0.24)]"
                        : "text-[var(--text-secondary)] hover:bg-[var(--surface-soft)] hover:text-[var(--text-primary)]"
                    )}
                  >
                    <div
                      className={cn(
                        "flex h-10 w-10 items-center justify-center rounded-2xl border transition",
                        active
                          ? "border-white/20 bg-white/15 text-white"
                          : "border-[var(--border-color)] bg-[var(--surface-soft)] text-[var(--text-secondary)] group-hover:border-[color:rgba(59,130,246,0.25)] group-hover:text-[var(--primary)]"
                      )}
                    >
                      <Icon className="h-4 w-4" />
                    </div>
                    <div>
                      <span className="block font-medium">{item.label}</span>
                      <span
                        className={cn(
                          "mt-0.5 block text-xs",
                          active ? "text-white/75" : "text-[var(--text-secondary)] group-hover:text-[var(--text-primary)]"
                        )}
                      >
                        {item.href === "/chat"
                          ? "AI conversations"
                          : item.href === "/knowledge-base"
                            ? "Document operations"
                            : item.href === "/summaries"
                              ? "Briefing center"
                              : item.href === "/settings"
                                ? "Workspace config"
                                : "Mission control"}
                      </span>
                    </div>
                  </Link>
                );
              })}
            </nav>

            <div className="panel-muted p-4">
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--text-secondary)]">
                  Recent chats
                </p>
                <button
                  onClick={() => setPaletteOpen(true)}
                  className="inline-flex items-center gap-2 rounded-full border border-[var(--border-color)] bg-[var(--surface-soft)] px-3 py-1.5 text-[11px] uppercase tracking-[0.16em] text-[var(--text-secondary)] transition hover:border-[color:rgba(59,130,246,0.3)] hover:text-[var(--primary)]"
                >
                  <Command className="h-3 w-3" />
                  search
                </button>
              </div>
              <div className="mt-4 space-y-2">
                {sessionsQuery.data?.sessions.slice(0, 5).map((session) => (
                  <Link
                    key={session.id}
                    href={`/chat?session=${session.id}`}
                    className="block rounded-[20px] border border-transparent bg-[var(--surface-soft)] px-4 py-3 text-sm text-[var(--text-secondary)] transition hover:border-[color:rgba(59,130,246,0.22)] hover:text-[var(--text-primary)]"
                  >
                    <p className="font-medium">{session.title}</p>
                    <p className="mt-1 text-xs text-[var(--text-secondary)]">
                      Updated {new Date(session.updated_at).toLocaleDateString()}
                    </p>
                  </Link>
                ))}
                {!sessionsQuery.data?.sessions.length ? (
                  <div className="rounded-[22px] border border-dashed border-[var(--border-color)] bg-[var(--surface-soft)] px-4 py-6 text-center">
                    <p className="text-sm text-[var(--text-secondary)]">No recent chats yet.</p>
                    <p className="mt-1 text-xs text-[var(--text-secondary)]">
                      Start a conversation and it will appear here.
                    </p>
                  </div>
                ) : null}
              </div>
            </div>

            <div className="panel-muted p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--text-secondary)]">
                Workspace pulse
              </p>
              <div className="mt-4 space-y-3 text-sm">
                <div className="flex items-center justify-between text-[var(--text-primary)]">
                  <span>Knowledge base</span>
                  <StatusBadge
                    label={documentsQuery.data?.documents.length ? "active" : "empty"}
                    tone={documentsQuery.data?.documents.length ? "ready" : "default"}
                  />
                </div>
                <div className="flex items-center justify-between text-[var(--text-primary)]">
                  <span>Recent sessions</span>
                  <span className="text-[var(--text-secondary)]">{sessionsQuery.data?.sessions.length ?? 0}</span>
                </div>
                <div className="flex items-center justify-between text-[var(--text-primary)]">
                  <span>Premium mode</span>
                  <span className="inline-flex items-center gap-2 text-[var(--primary)]">
                    <Zap className="h-3.5 w-3.5" />
                    enabled
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="panel-muted p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--text-secondary)]">
              Signed in
            </p>
            <div className="mt-4 flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-[var(--text-primary)]">{user.displayName}</p>
                <p className="mt-1 text-sm text-[var(--text-secondary)]">{user.email || "local workspace mode"}</p>
                <div className="mt-3">
                  <StatusBadge label="workspace session" tone="ready" subtle />
                </div>
              </div>
              <button
                onClick={() => {
                  logout();
                  pushToast({
                    tone: "info",
                    title: "Signed out",
                    description: "You can log back in anytime from the workspace login page."
                  });
                  router.replace("/login");
                }}
                className="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-[var(--border-color)] bg-[var(--surface-soft)] text-[var(--text-secondary)] transition hover:border-[color:rgba(239,68,68,0.22)] hover:bg-[color:rgba(239,68,68,0.08)] hover:text-[var(--error)]"
                aria-label="Sign out"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          </div>
        </aside>

        <main className="min-w-0 flex-1 pt-20 lg:pt-0">
          <TopBar title={heading} subtitle={subtitle} onOpenPalette={() => setPaletteOpen(true)} />
          {children}
        </main>
      </div>
    </div>
  );
}
