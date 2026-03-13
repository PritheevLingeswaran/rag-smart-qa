"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Bell,
  BookOpen,
  Bot,
  Command,
  Database,
  LayoutDashboard,
  LogOut,
  MessageSquare,
  Search,
  Settings2,
  Sparkles,
  Terminal,
  Zap
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { CommandPalette } from "@/components/command-palette";
import { LoadingSkeleton } from "@/components/loading-skeleton";
import { StatusBadge } from "@/components/status-badge";
import { useToast } from "@/components/toast-provider";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/workspace", label: "Dashboard", icon: LayoutDashboard },
  { href: "/chat", label: "Intelligent Chat", icon: MessageSquare },
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

  const subtitle = useMemo(() => {
    if (pathname === "/chat") {
      return "Navigate your retrieval system with citations, follow-ups, and grounded answer review.";
    }
    if (pathname === "/knowledge-base") {
      return "Organize uploads, indexing, and document operations from one place.";
    }
    if (pathname === "/summaries") {
      return "Review generated briefings and move back into the source material quickly.";
    }
    if (pathname === "/settings") {
      return "Inspect runtime configuration, feature flags, and retrieval defaults.";
    }
    return "Welcome back. Systems are optimal.";
  }, [pathname]);

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
    <div className="min-h-screen">
      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        sessions={sessionsQuery.data?.sessions ?? []}
        documents={documentsQuery.data?.documents ?? []}
      />

      <div className="relative flex min-h-screen">
        <aside className="fixed inset-y-0 left-0 z-40 hidden w-72 flex-col border-r border-white/5 bg-[rgba(21,27,40,0.42)] p-6 backdrop-blur-2xl lg:flex">
          <div className="flex items-center gap-4 px-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-[#3B82F6] to-[#8B5CF6] shadow-lg shadow-indigo-500/20">
              <Bot className="h-5 w-5 text-white" />
            </div>
            <span className="text-lg font-extrabold tracking-tight">
              rag<span className="text-indigo-400">smart</span>
            </span>
          </div>

          <nav className="mt-8 space-y-2">
            {nav.map((item) => {
              const Icon = item.icon;
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "relative flex items-center gap-4 rounded-2xl px-4 py-3 text-[13px] font-bold transition-all",
                    active
                      ? "bg-indigo-500/10 text-indigo-300"
                      : "text-slate-500 hover:bg-white/5 hover:text-white"
                  )}
                >
                  {active ? <span className="absolute left-0 top-1/4 h-1/2 w-1 rounded-r-full bg-indigo-400 shadow-[0_0_15px_#6366F1]" /> : null}
                  <Icon className="h-5 w-5" />
                  <span>{item.label}</span>
                </Link>
              );
            })}

            <div className="pb-4 pt-8">
              <span className="px-4 text-[10px] font-bold uppercase tracking-[0.2em] text-slate-600">System</span>
            </div>

            <button
              onClick={() => setPaletteOpen(true)}
              className="flex w-full items-center gap-4 rounded-2xl px-4 py-3.5 font-bold text-slate-500 transition hover:bg-white/5 hover:text-white"
            >
              <Command className="h-5 w-5" />
              <span>Command search</span>
            </button>
            <div className="flex items-center gap-4 rounded-2xl px-4 py-3.5 font-bold text-slate-500">
              <Terminal className="h-5 w-5" />
              <span>API Explorer</span>
            </div>
          </nav>

          <div className="mt-auto space-y-4">
            <div className="surface-card rounded-[1.5rem] bg-gradient-to-br from-indigo-500/10 to-transparent p-4">
              <div className="mb-3 flex h-8 w-8 items-center justify-center rounded-full bg-indigo-500/20">
                <Zap className="h-4 w-4 text-indigo-300" />
              </div>
              <p className="text-[11px] font-bold text-white">Scale your flow</p>
              <p className="mt-1 text-[11px] leading-5 text-slate-400">
                Unlock unlimited vector embeddings and advanced RAG reranking.
              </p>
            </div>

            <div className="panel-muted p-4">
              <p className="text-[13px] font-bold text-white">{user.displayName}</p>
              <p className="mt-1 text-xs text-slate-500">{user.email || "local workspace mode"}</p>
              <div className="mt-3 flex items-center justify-between">
                <StatusBadge label="workspace session" tone="ready" subtle />
                <button
                  onClick={() => {
                    logout();
                    pushToast({
                      tone: "info",
                      title: "Signed out",
                      description: "Your local workspace session has been cleared."
                    });
                    router.replace("/login");
                  }}
                  className="flex h-10 w-10 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-slate-400 transition hover:bg-white/10 hover:text-white"
                  aria-label="Sign out"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        </aside>

        <main className="min-h-screen flex-1 p-6 lg:ml-72 lg:p-12">
          <header className="mb-12 flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
            <div>
              <h1 className="text-[28px] font-extrabold tracking-tight">
                Intelligence <span className="text-gradient">Hub</span>
              </h1>
              <div className="mt-1 flex items-center gap-2 text-[13px] font-medium text-slate-500">
                <Sparkles className="h-4 w-4" />
                <span>{subtitle}</span>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <button
                onClick={() => setPaletteOpen(true)}
                className="group relative hidden md:block"
              >
                <input
                  readOnly
                  value=""
                  placeholder="Search knowledge..."
                  className="w-64 rounded-2xl border border-white/10 bg-white/5 px-5 py-3 pr-12 text-[13px] outline-none transition group-hover:border-indigo-400/50"
                />
                <Search className="absolute right-4 top-3.5 h-4 w-4 text-slate-500" />
              </button>

              <button className="rounded-2xl border border-white/10 bg-white/5 p-3 text-slate-400 transition hover:bg-white/10 hover:text-white">
                <Bell className="h-5 w-5" />
              </button>

              <div className="hidden h-10 w-px bg-white/10 md:block" />

              <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-2">
                <div className="h-8 w-8 rounded-full bg-gradient-to-tr from-[#3B82F6] to-[#8B5CF6]" />
                <div>
                  <p className="text-[13px] font-bold">{user.displayName}</p>
                  <p className="text-xs text-slate-500">{documentsQuery.data?.documents.length ?? 0} docs</p>
                </div>
              </div>
            </div>
          </header>

          {children}
        </main>
      </div>
    </div>
  );
}
