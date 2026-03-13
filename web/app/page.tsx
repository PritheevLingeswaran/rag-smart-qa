"use client";

import {
  ArrowRight,
  BrainCircuit,
  DatabaseZap,
  FileStack,
  LockKeyhole,
  MessagesSquare,
  PlayCircle,
  ShieldCheck,
  Sparkles,
  Workflow
} from "lucide-react";
import Link from "next/link";

const features = [
  {
    icon: FileStack,
    title: "Multi-document ingestion",
    body: "Upload files, track chunking, and build a searchable knowledge system in one flow."
  },
  {
    icon: DatabaseZap,
    title: "Hybrid vector retrieval",
    body: "Blend semantic and lexical retrieval for better evidence coverage and grounded recall."
  },
  {
    icon: MessagesSquare,
    title: "Cited AI answers",
    body: "Every answer stays connected to source passages so users can verify what the model used."
  },
  {
    icon: BrainCircuit,
    title: "Summary generation",
    body: "Turn long files into executive briefings, key insights, and rapid review summaries."
  },
  {
    icon: Workflow,
    title: "Knowledge workflows",
    body: "Move from upload to chat to summary review without ever leaving the product surface."
  },
  {
    icon: ShieldCheck,
    title: "Secure product posture",
    body: "Built with typed APIs, health checks, feature flags, and a clean backend integration seam."
  }
];

export default function LandingPage() {
  return (
    <div className="min-h-screen text-[var(--text-primary)]">
      <div className="app-bg-grid min-h-screen">
        <nav className="fixed inset-x-0 top-0 z-50 px-6 py-5 lg:px-12">
          <div className="mx-auto flex max-w-7xl items-center justify-between rounded-[1.75rem] border border-white/10 bg-[rgba(21,27,40,0.45)] px-5 py-4 backdrop-blur-xl">
            <Link href="/" className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-[#3B82F6] via-[#6366F1] to-[#8B5CF6] shadow-lg shadow-indigo-500/20">
                <BrainCircuit className="h-5 w-5 text-white" />
              </div>
              <span className="text-lg font-extrabold tracking-tight">
                rag<span className="text-indigo-400">smart</span>qa
              </span>
            </Link>

            <div className="hidden items-center gap-8 text-[13px] font-semibold text-slate-400 md:flex">
              <a href="#features" className="transition hover:text-white">Capabilities</a>
              <a href="#demo" className="transition hover:text-white">Interface</a>
              <a href="#security" className="transition hover:text-white">Security</a>
              <Link href="/login" className="text-white">Sign in</Link>
              <Link href="/workspace" className="btn-primary rounded-full px-5 py-2.5">
                Launch dashboard
              </Link>
            </div>
          </div>
        </nav>

        <main className="mx-auto max-w-7xl px-6 pb-24 pt-32 lg:px-12">
          <section className="grid items-center gap-16 lg:grid-cols-2">
            <div>
              <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-3 py-1 text-xs font-bold uppercase tracking-[0.24em] text-indigo-300">
                <Sparkles className="h-3.5 w-3.5" />
                Intelligent knowledge flow
              </div>
              <h1 className="text-5xl font-black leading-[1.05] lg:text-7xl">
                Conversations
                <br />
                <span className="text-gradient">with clarity.</span>
              </h1>
              <p className="mt-6 max-w-xl text-lg leading-8 text-slate-400">
                Transform static documentation into an active knowledge ecosystem with seamless ingestion,
                hybrid retrieval, grounded answers, and precision summaries.
              </p>
              <div className="mt-10 flex flex-col gap-4 sm:flex-row">
                <Link href="/workspace" className="btn-primary gap-3 rounded-2xl px-7 py-3.5">
                  Deploy my knowledge base
                  <Sparkles className="h-5 w-5" />
                </Link>
                <Link href="/login" className="btn-secondary gap-3 rounded-2xl px-7 py-3.5">
                  Watch technical demo
                  <PlayCircle className="h-5 w-5" />
                </Link>
              </div>
            </div>

            <div id="demo" className="relative hidden lg:block">
              <div className="absolute -inset-10 rounded-full bg-indigo-500/20 blur-[120px]" />
              <div className="panel premium-ring relative z-10 rounded-[2rem] p-6">
                <div className="mb-8 flex items-center justify-between">
                  <div className="flex gap-2">
                    <div className="h-3 w-3 rounded-full bg-rose-400/60" />
                    <div className="h-3 w-3 rounded-full bg-amber-400/60" />
                    <div className="h-3 w-3 rounded-full bg-emerald-400/60" />
                  </div>
                  <div className="text-[10px] font-mono tracking-[0.3em] text-slate-500">
                    KNOWLEDGE_OS / DASHBOARD
                  </div>
                </div>

                <div className="space-y-6">
                  <div className="surface-card flex items-center gap-4 p-4">
                    <div className="icon-chip h-12 w-12">
                      <FileStack className="h-5 w-5" />
                    </div>
                    <div className="flex-1">
                      <div className="mb-2 h-2.5 w-32 rounded-full bg-slate-700" />
                      <div className="h-2 w-48 rounded-full bg-slate-800" />
                    </div>
                    <div className="rounded-full bg-blue-500/10 px-2 py-1 text-[10px] font-bold uppercase tracking-[0.18em] text-blue-300">
                      analyzing
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="surface-card p-5">
                      <p className="metric-label">Vectors indexed</p>
                      <p className="mt-3 text-2xl font-black">14,209</p>
                    </div>
                    <div className="surface-card p-5">
                      <p className="metric-label">Grounding score</p>
                      <p className="mt-3 text-2xl font-black text-emerald-400">98.2%</p>
                    </div>
                  </div>

                  <div className="surface-card p-5">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-bold">Ask the workspace</p>
                        <p className="mt-1 text-sm text-slate-400">Citations, summaries, and retrieval-aware answers.</p>
                      </div>
                      <MessagesSquare className="h-5 w-5 text-indigo-300" />
                    </div>
                    <div className="mt-4 rounded-2xl border border-white/10 bg-black/20 px-4 py-4 text-sm text-slate-300">
                      &quot;Which sections of our compliance handbook describe vendor security reviews?&quot;
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2">
                      {["PDF upload", "Source citations", "Hybrid RRF", "Answer summaries"].map((item) => (
                        <span key={item} className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-bold uppercase tracking-[0.14em] text-slate-300">
                          {item}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section id="features" className="mt-28">
            <div className="max-w-2xl">
              <p className="section-eyebrow">Capabilities</p>
              <h2 className="section-title">From document ingestion to grounded conversation</h2>
              <p className="section-copy">
                These pages now follow the darker product language from your reference files instead of the previous website.
              </p>
            </div>
            <div className="mt-10 grid gap-6 md:grid-cols-2 xl:grid-cols-3">
              {features.map((feature) => {
                const Icon = feature.icon;
                return (
                  <div key={feature.title} className="surface-card rounded-[2rem] p-6">
                    <div className="icon-chip">
                      <Icon className="h-5 w-5" />
                    </div>
                    <h3 className="mt-5 text-lg font-extrabold">{feature.title}</h3>
                    <p className="mt-3 text-sm leading-7 text-slate-400">{feature.body}</p>
                  </div>
                );
              })}
            </div>
          </section>

          <section className="mt-28 grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
            <div className="panel rounded-[2rem] p-8">
              <p className="section-eyebrow">Why this is better</p>
              <h2 className="mt-3 text-3xl font-black tracking-tight">A real AI product surface, not a generic dashboard</h2>
              <div className="mt-8 space-y-4">
                {[
                  "Ground every answer in document evidence",
                  "Manage the corpus with status, metadata, and summaries",
                  "Present a premium public site and premium product app with one brand system"
                ].map((item) => (
                  <div key={item} className="surface-card flex items-start gap-3 p-4">
                    <ShieldCheck className="mt-0.5 h-5 w-5 text-indigo-300" />
                    <p className="text-sm leading-7 text-slate-300">{item}</p>
                  </div>
                ))}
              </div>
            </div>

            <div id="security" className="panel rounded-[2rem] p-8">
              <p className="section-eyebrow">Security</p>
              <h2 className="mt-3 text-3xl font-black tracking-tight">Typed APIs, health checks, and clean auth seams</h2>
              <p className="mt-4 text-sm leading-7 text-slate-400">
                rag-smart-qa keeps the real FastAPI backend, vector search, and chat/session logic intact while upgrading the interface to look launch-ready.
              </p>
              <div className="mt-8 grid gap-3">
                {["FastAPI backend", "Local-first document storage", "Vector search integration", "Session-aware chat history"].map((item) => (
                  <div key={item} className="surface-card flex items-center justify-between p-4 text-sm font-bold">
                    <span>{item}</span>
                    <LockKeyhole className="h-4 w-4 text-indigo-300" />
                  </div>
                ))}
              </div>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}
