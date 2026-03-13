"use client";

import { Bot, KeyRound, LockKeyhole, Mail, MoveRight, ShieldCheck, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { StatusBadge } from "@/components/status-badge";
import { useToast } from "@/components/toast-provider";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const { pushToast } = useToast();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!email.trim()) {
      pushToast({
        tone: "error",
        title: "Email required",
        description: "Enter a workspace email to create a local session."
      });
      return;
    }

    login({ displayName, email });
    pushToast({
      tone: "success",
      title: "Welcome back",
      description: "Your workspace session is active."
    });
    router.replace("/workspace");
  }

  return (
    <div className="app-bg-grid min-h-screen overflow-hidden px-4 py-8">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(59,130,246,0.18),transparent_25%),radial-gradient(circle_at_bottom_right,rgba(139,92,246,0.18),transparent_24%)]" />
      <div className="relative mx-auto grid min-h-[calc(100vh-4rem)] max-w-[1450px] items-center gap-6 lg:grid-cols-[1.05fr_0.95fr]">
        <section className="premium-ring panel panel-glow overflow-hidden p-8 md:p-10 lg:p-12">
          <div className="flex items-center gap-4">
            <div className="flex h-16 w-16 items-center justify-center rounded-[28px] bg-[linear-gradient(135deg,#3B82F6,#6366F1,#8B5CF6)] text-white shadow-[0_20px_45px_rgba(59,130,246,0.28)]">
              <Bot className="h-7 w-7" />
            </div>
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-[var(--primary)]">
                rag-smart-qa
              </p>
              <h1 className="mt-2 text-4xl font-semibold tracking-[-0.04em] text-[var(--text-primary)] md:text-5xl">
                Sign in to your AI retrieval workspace
              </h1>
            </div>
          </div>

          <p className="mt-6 max-w-2xl text-base leading-8 text-[var(--text-secondary)]">
            This login surface is built to feel recruiter-ready: premium presentation, clear trust signals, and a session flow already wired to the backend&apos;s user-isolation header seam.
          </p>

          <div className="mt-8 flex flex-wrap gap-2">
            <StatusBadge label="local auth session" tone="ready" />
            <StatusBadge label="provider-ready architecture" tone="queued" />
            <StatusBadge label="single user fallback" tone="queued" subtle />
          </div>

          <div className="mt-10 grid gap-4 md:grid-cols-3">
            {[
              {
                icon: ShieldCheck,
                title: "Secure-feeling entry",
                body: "A polished front door for demos, portfolio walkthroughs, and future provider wiring."
              },
              {
                icon: Sparkles,
                title: "Session-aware UI",
                body: "The workspace now remembers who is signed in and routes requests with the user header."
              },
              {
                icon: LockKeyhole,
                title: "Provider-ready seam",
                body: "The current flow works locally while staying clean for Clerk or Firebase later."
              }
            ].map((item) => {
              const Icon = item.icon;
              return (
                <div key={item.title} className="panel-muted p-5">
                  <div className="icon-chip">
                    <Icon className="h-4 w-4" />
                  </div>
                  <p className="mt-4 text-lg font-semibold text-[var(--text-primary)]">{item.title}</p>
                  <p className="mt-2 text-sm leading-7 text-[var(--text-secondary)]">{item.body}</p>
                </div>
              );
            })}
          </div>
        </section>

        <section className="panel panel-glow premium-ring overflow-hidden p-8 md:p-10">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-[var(--primary)]">
                Workspace access
              </p>
              <h2 className="mt-2 text-3xl font-semibold tracking-[-0.03em] text-[var(--text-primary)]">
                Continue into the product
              </h2>
            </div>
            <div className="icon-chip h-14 w-14 rounded-[24px]">
              <KeyRound className="h-5 w-5" />
            </div>
          </div>

          <form onSubmit={handleSubmit} className="mt-8 space-y-5">
            <label className="block">
              <span className="mb-2 block text-sm font-medium text-[var(--text-primary)]">Display name</span>
              <div className="flex items-center gap-3 rounded-[24px] border border-[var(--border-color)] bg-[var(--surface-soft)] px-4 py-4 transition focus-within:border-[color:rgba(59,130,246,0.3)]">
                <Sparkles className="h-4 w-4 text-[var(--text-muted)]" />
                <input
                  value={displayName}
                  onChange={(event) => setDisplayName(event.target.value)}
                  placeholder="Pritheev"
                  className="w-full bg-transparent text-sm text-[var(--text-primary)] outline-none placeholder:text-[var(--text-muted)]"
                />
              </div>
            </label>

            <label className="block">
              <span className="mb-2 block text-sm font-medium text-[var(--text-primary)]">Email</span>
              <div className="flex items-center gap-3 rounded-[24px] border border-[var(--border-color)] bg-[var(--surface-soft)] px-4 py-4 transition focus-within:border-[color:rgba(59,130,246,0.3)]">
                <Mail className="h-4 w-4 text-[var(--text-muted)]" />
                <input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@workspace.ai"
                  className="w-full bg-transparent text-sm text-[var(--text-primary)] outline-none placeholder:text-[var(--text-muted)]"
                />
              </div>
            </label>

            <label className="block">
              <span className="mb-2 block text-sm font-medium text-[var(--text-primary)]">Password</span>
              <div className="flex items-center gap-3 rounded-[24px] border border-[var(--border-color)] bg-[var(--surface-soft)] px-4 py-4 transition focus-within:border-[color:rgba(59,130,246,0.3)]">
                <LockKeyhole className="h-4 w-4 text-[var(--text-muted)]" />
                <input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Enter any password for local mode"
                  className="w-full bg-transparent text-sm text-[var(--text-primary)] outline-none placeholder:text-[var(--text-muted)]"
                />
              </div>
              <p className="mt-2 text-xs uppercase tracking-[0.18em] text-[var(--text-secondary)]">
                Demo-ready local mode. Password is not verified yet.
              </p>
            </label>

            <button
              type="submit"
              className="btn-primary w-full gap-2 py-4"
            >
              Enter workspace
              <MoveRight className="h-4 w-4" />
            </button>
          </form>

          <div className="mt-6 rounded-[24px] border border-[var(--border-color)] bg-[var(--surface-soft)] p-5">
            <p className="text-sm font-semibold text-[var(--text-primary)]">What this login enables</p>
            <ul className="mt-3 space-y-2 text-sm leading-7 text-[var(--text-secondary)]">
              <li>Personal workspace identity in the UI</li>
              <li>`x-user-id` header forwarded to your backend APIs</li>
              <li>Clean future upgrade path to real auth providers</li>
            </ul>
          </div>

          <a
            href="/"
            className="mt-5 inline-flex items-center gap-2 text-sm font-medium text-[var(--text-secondary)] transition hover:text-[var(--primary)]"
          >
            <MoveRight className="h-4 w-4 rotate-180" />
            Back to product website
          </a>
        </section>
      </div>
    </div>
  );
}
