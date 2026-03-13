"use client";

import {
  ArrowRight,
  BadgeCheck,
  BookOpenText,
  Bot,
  BrainCircuit,
  Database,
  Files,
  Gauge,
  Layers3,
  SearchCheck,
  ShieldCheck,
  Workflow
} from "lucide-react";
import Link from "next/link";

const chips = [
  "Hybrid Retrieval",
  "Grounded Answers",
  "Source Citations",
  "Multi-Document Upload",
  "Summaries",
  "Load-Tested API"
];

const features = [
  {
    icon: Files,
    title: "Multi-document upload",
    body: "Upload PDFs, markdown, HTML, and plain text into a managed knowledge base with ingestion status and metadata."
  },
  {
    icon: SearchCheck,
    title: "Hybrid retrieval",
    body: "Expose dense, BM25, weighted hybrid, and RRF retrieval modes directly in the product experience."
  },
  {
    icon: ShieldCheck,
    title: "Grounded answers with citations",
    body: "Every response can point back to the evidence used so the assistant feels trustworthy and reviewable."
  },
  {
    icon: BookOpenText,
    title: "Knowledge base management",
    body: "Browse, filter, delete, reindex, and inspect documents with a UI that feels like a real SaaS product."
  },
  {
    icon: BrainCircuit,
    title: "AI-generated summaries",
    body: "Summaries, key insights, and important points are ready for fast skimming before deeper exploration."
  },
  {
    icon: Gauge,
    title: "Evaluation and observability",
    body: "The architecture stays practical for testing, health checks, runtime inspection, and performance work."
  }
];

const workflow = [
  "Upload files",
  "Chunk + embed + index",
  "Ask questions",
  "Retrieve evidence",
  "Generate grounded answer",
  "Inspect citations"
];

const useCases = [
  "Research assistant",
  "Internal company docs assistant",
  "Policy and compliance lookup",
  "Technical documentation Q&A",
  "Personal knowledge base"
];

const architecture = [
  "Next.js App Router frontend",
  "Tailwind design system with dark and light mode",
  "FastAPI backend with typed APIs",
  "Local-first storage and metadata layer",
  "FAISS or Chroma retrieval backends",
  "Session-aware chat and citation lookup"
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)]">
      <div className="absolute inset-x-0 top-0 -z-10 h-[560px] bg-[radial-gradient(circle_at_top_left,rgba(59,130,246,0.18),transparent_30%),radial-gradient(circle_at_top_right,rgba(139,92,246,0.16),transparent_28%),linear-gradient(180deg,rgba(99,102,241,0.06),transparent_72%)]" />

      <header className="mx-auto flex w-full max-w-[1280px] items-center justify-between px-4 py-5 md:px-6">
        <Link href="/" className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[linear-gradient(135deg,#3B82F6,#6366F1,#8B5CF6)] text-white shadow-[0_18px_40px_rgba(59,130,246,0.24)]">
            <Bot className="h-5 w-5" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--text-secondary)]">
              rag-smart-qa
            </p>
            <p className="text-sm font-semibold text-[var(--text-primary)]">
              Knowledge copilots for your documents
            </p>
          </div>
        </Link>
        <nav className="hidden items-center gap-8 md:flex">
          <a href="#features" className="text-sm text-[var(--text-secondary)] transition hover:text-[var(--text-primary)]">
            Features
          </a>
          <a href="#how-it-works" className="text-sm text-[var(--text-secondary)] transition hover:text-[var(--text-primary)]">
            How it works
          </a>
          <a href="#use-cases" className="text-sm text-[var(--text-secondary)] transition hover:text-[var(--text-primary)]">
            Use cases
          </a>
          <a href="#architecture" className="text-sm text-[var(--text-secondary)] transition hover:text-[var(--text-primary)]">
            Architecture
          </a>
        </nav>
        <div className="flex items-center gap-3">
          <Link href="/login" className="hidden rounded-full border border-[var(--border-color)] px-4 py-2.5 text-sm font-medium text-[var(--text-primary)] transition hover:border-[var(--primary)] hover:text-[var(--primary)] md:inline-flex">
            Sign in
          </Link>
          <Link href="/workspace" className="inline-flex items-center gap-2 rounded-full bg-[var(--primary)] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[var(--primary-hover)]">
            Launch workspace
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </header>

      <main>
        <section className="mx-auto grid w-full max-w-[1280px] gap-12 px-4 pb-20 pt-10 md:px-6 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:pt-16">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-[color:rgba(59,130,246,0.18)] bg-[color:rgba(59,130,246,0.08)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--primary)]">
              <BadgeCheck className="h-3.5 w-3.5" />
              Premium AI knowledge product
            </div>
            <h1 className="mt-6 max-w-4xl text-5xl font-semibold tracking-[-0.06em] text-[var(--text-primary)] md:text-6xl lg:text-7xl">
              Ask your documents anything, with grounded answers and citations.
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-[var(--text-secondary)]">
              rag-smart-qa turns PDFs, notes, and internal docs into a searchable knowledge copilot with hybrid retrieval, cited answers, summaries, and a production-style RAG workflow.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/workspace" className="btn-primary px-6 py-4">
                Try the demo
              </Link>
              <Link href="/knowledge-base" className="btn-secondary px-6 py-4">
                View knowledge base
              </Link>
            </div>
            <div className="mt-8 flex flex-wrap gap-2">
              {chips.map((chip) => (
                <span key={chip} className="rounded-full border border-[var(--border-color)] bg-[var(--surface-soft)] px-3 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-[var(--text-secondary)]">
                  {chip}
                </span>
              ))}
            </div>
          </div>

          <div className="relative">
            <div className="absolute inset-8 -z-10 rounded-[36px] bg-[linear-gradient(135deg,rgba(59,130,246,0.18),rgba(99,102,241,0.12),rgba(139,92,246,0.18))] blur-3xl" />
            <div className="panel premium-border overflow-hidden p-4 md:p-5">
              <div className="rounded-[28px] border border-[var(--border-color)] bg-[var(--bg-secondary)] p-4">
                <div className="flex items-center justify-between border-b border-[var(--border-color)] pb-4">
                  <div>
                    <p className="section-eyebrow">Product preview</p>
                    <h2 className="mt-2 text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
                      Workspace chat
                    </h2>
                  </div>
                  <span className="rounded-full bg-[color:rgba(34,197,94,0.14)] px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.14em] text-[var(--success)]">
                    citations live
                  </span>
                </div>

                <div className="mt-4 grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
                  <div className="rounded-[24px] border border-[var(--border-color)] bg-[var(--bg-primary)] p-4">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[linear-gradient(135deg,#3B82F6,#8B5CF6)] text-white">
                        <Bot className="h-4 w-4" />
                      </div>
                      <div>
                        <p className="text-sm font-semibold">Answer card</p>
                        <p className="text-xs text-[var(--text-secondary)]">
                          Hybrid RRF rerank • 812 ms • 92% confidence
                        </p>
                      </div>
                    </div>
                    <p className="mt-4 text-sm leading-7 text-[var(--text-secondary)]">
                      The system retrieves semantically relevant chunks, cross-checks them with lexical recall, and responds with evidence-backed citations instead of unsupported claims.
                    </p>
                    <div className="mt-4 flex flex-wrap gap-2">
                      {["policy-handbook.pdf p12", "onboarding-notes.md p1", "security-guide.html p4"].map((item) => (
                        <span key={item} className="rounded-full border border-[var(--border-color)] bg-[var(--surface-soft)] px-3 py-2 text-xs font-semibold text-[var(--text-secondary)]">
                          {item}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div className="rounded-[24px] border border-[var(--border-color)] bg-[var(--bg-primary)] p-4">
                      <p className="metric-label">Corpus health</p>
                      <div className="mt-4 grid grid-cols-2 gap-3">
                        {[
                          ["Documents", "24"],
                          ["Chunks", "1,842"],
                          ["Summaries", "18"],
                          ["Ready", "96%"]
                        ].map(([label, value]) => (
                          <div key={label} className="rounded-[20px] border border-[var(--border-color)] bg-[var(--surface-soft)] p-3">
                            <p className="text-xs text-[var(--text-secondary)]">{label}</p>
                            <p className="mt-2 text-xl font-semibold text-[var(--text-primary)]">{value}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="rounded-[24px] border border-[var(--border-color)] bg-[var(--bg-primary)] p-4">
                      <p className="metric-label">Why teams use it</p>
                      <div className="mt-3 space-y-3">
                        {[
                          "Ground every answer in source evidence",
                          "Manage your document corpus like a real product",
                          "Expose operational detail without losing polish"
                        ].map((item) => (
                          <div key={item} className="flex items-start gap-3 rounded-[18px] bg-[var(--surface-soft)] px-3 py-3">
                            <BadgeCheck className="mt-0.5 h-4 w-4 text-[var(--primary)]" />
                            <p className="text-sm text-[var(--text-secondary)]">{item}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="mx-auto w-full max-w-[1280px] px-4 py-6 md:px-6">
          <div className="panel grid gap-4 p-6 md:grid-cols-3">
            {[
              ["Grounded RAG", "Cited answers that keep the assistant honest."],
              ["Knowledge ops", "Upload, reindex, filter, and manage your corpus."],
              ["Production posture", "Typed APIs, health endpoints, and evaluation hooks."]
            ].map(([title, body]) => (
              <div key={title} className="rounded-[24px] border border-[var(--border-color)] bg-[var(--surface-soft)] p-5">
                <p className="text-lg font-semibold text-[var(--text-primary)]">{title}</p>
                <p className="mt-2 text-sm leading-7 text-[var(--text-secondary)]">{body}</p>
              </div>
            ))}
          </div>
        </section>

        <section id="features" className="mx-auto w-full max-w-[1280px] px-4 py-20 md:px-6">
          <div className="max-w-3xl">
            <p className="section-eyebrow">Features</p>
            <h2 className="section-title">Everything you need to ship a serious document intelligence product</h2>
            <p className="section-copy">
              The experience spans ingestion, retrieval, grounded generation, citation review, summaries, and operational visibility without drifting into a generic admin template.
            </p>
          </div>
          <div className="mt-10 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {features.map((feature) => {
              const Icon = feature.icon;
              return (
                <div key={feature.title} className="panel panel-hover p-6">
                  <div className="icon-chip">
                    <Icon className="h-5 w-5" />
                  </div>
                  <h3 className="mt-5 text-xl font-semibold text-[var(--text-primary)]">{feature.title}</h3>
                  <p className="mt-3 text-sm leading-7 text-[var(--text-secondary)]">{feature.body}</p>
                </div>
              );
            })}
          </div>
        </section>

        <section id="how-it-works" className="mx-auto w-full max-w-[1280px] px-4 py-20 md:px-6">
          <div className="grid gap-10 lg:grid-cols-[0.9fr_1.1fr]">
            <div>
              <p className="section-eyebrow">How it works</p>
              <h2 className="section-title">From file upload to grounded answer in a clean, inspectable pipeline</h2>
              <p className="section-copy">
                Upload files, build chunks and embeddings, retrieve evidence, and answer with citations users can actually inspect.
              </p>
            </div>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {workflow.map((step, index) => (
                <div key={step} className="panel p-5">
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--primary)]">
                    Step {index + 1}
                  </p>
                  <p className="mt-3 text-lg font-semibold text-[var(--text-primary)]">{step}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="mx-auto w-full max-w-[1280px] px-4 py-20 md:px-6">
          <div className="grid gap-5 lg:grid-cols-[1.05fr_0.95fr]">
            <div className="panel overflow-hidden p-7">
              <p className="section-eyebrow">Why this is better</p>
              <h2 className="section-title">A polished public story without sacrificing backend realism</h2>
              <div className="mt-8 grid gap-4 md:grid-cols-2">
                {[
                  {
                    icon: BrainCircuit,
                    title: "Trust through citations",
                    body: "Users can inspect supporting evidence instead of blindly accepting generated text."
                  },
                  {
                    icon: Layers3,
                    title: "Real retrieval control",
                    body: "Dense, BM25, and hybrid modes are product features, not hidden implementation details."
                  },
                  {
                    icon: Workflow,
                    title: "Clean operational flow",
                    body: "Upload, ingestion, summary generation, and chat history are surfaced with clarity."
                  },
                  {
                    icon: Gauge,
                    title: "Launch-ready polish",
                    body: "The UI is designed to hold up in demos, screenshots, recruiter reviews, and public publishing."
                  }
                ].map((item) => {
                  const Icon = item.icon;
                  return (
                    <div key={item.title} className="rounded-[24px] border border-[var(--border-color)] bg-[var(--surface-soft)] p-5">
                      <Icon className="h-5 w-5 text-[var(--primary)]" />
                      <p className="mt-4 text-lg font-semibold text-[var(--text-primary)]">{item.title}</p>
                      <p className="mt-2 text-sm leading-7 text-[var(--text-secondary)]">{item.body}</p>
                    </div>
                  );
                })}
              </div>
            </div>

            <div id="architecture" className="panel p-7">
              <p className="section-eyebrow">Architecture highlights</p>
              <h2 className="section-title">Modern app shell up front, typed RAG services underneath</h2>
              <div className="mt-6 space-y-3">
                {architecture.map((item) => (
                  <div key={item} className="flex items-start gap-3 rounded-[20px] border border-[var(--border-color)] bg-[var(--surface-soft)] px-4 py-4">
                    <BadgeCheck className="mt-0.5 h-4 w-4 text-[var(--primary)]" />
                    <p className="text-sm leading-7 text-[var(--text-secondary)]">{item}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section id="use-cases" className="mx-auto w-full max-w-[1280px] px-4 py-20 md:px-6">
          <div className="max-w-3xl">
            <p className="section-eyebrow">Use cases</p>
            <h2 className="section-title">Designed for teams and builders who need answers they can verify</h2>
            <p className="section-copy">
              The interface works for public demos, internal tools, and practical document-grounded workflows.
            </p>
          </div>
          <div className="mt-10 grid gap-5 md:grid-cols-2 xl:grid-cols-5">
            {useCases.map((item) => (
              <div key={item} className="panel p-5">
                <p className="text-base font-semibold text-[var(--text-primary)]">{item}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="mx-auto w-full max-w-[1280px] px-4 pb-20 md:px-6">
          <div className="overflow-hidden rounded-[36px] border border-[var(--border-color)] bg-[linear-gradient(135deg,rgba(59,130,246,0.12),rgba(99,102,241,0.12),rgba(139,92,246,0.16))] p-8 md:p-10">
            <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-white/80">Ready to publish</p>
            <h2 className="max-w-3xl text-4xl font-semibold tracking-[-0.05em] text-white md:text-5xl">
              Launch a serious AI product experience, not just another dashboard.
            </h2>
            <p className="mt-4 max-w-2xl text-base leading-8 text-white/80">
              rag-smart-qa now pairs a public-facing product story with a polished workspace for ingestion, cited chat, summaries, and knowledge management.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/workspace" className="inline-flex items-center gap-2 rounded-2xl bg-white px-6 py-4 text-sm font-semibold text-slate-950 transition hover:bg-slate-100">
                Launch workspace
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link href="/login" className="inline-flex items-center gap-2 rounded-2xl border border-white/30 px-6 py-4 text-sm font-semibold text-white transition hover:bg-white/10">
                Sign in
              </Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-[var(--border-color)] bg-[var(--bg-secondary)]">
        <div className="mx-auto grid w-full max-w-[1280px] gap-10 px-4 py-12 md:grid-cols-[1.2fr_0.8fr_0.8fr_0.8fr] md:px-6">
          <div>
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[linear-gradient(135deg,#3B82F6,#6366F1,#8B5CF6)] text-white">
                <Bot className="h-4 w-4" />
              </div>
              <div>
                <p className="text-sm font-semibold text-[var(--text-primary)]">rag-smart-qa</p>
                <p className="text-sm text-[var(--text-secondary)]">
                  Upload documents. Retrieve grounded answers. Cite every response.
                </p>
              </div>
            </div>
          </div>
          <div>
            <p className="text-sm font-semibold text-[var(--text-primary)]">Product</p>
            <div className="mt-4 space-y-3 text-sm text-[var(--text-secondary)]">
              <Link href="/workspace" className="block transition hover:text-[var(--text-primary)]">Workspace</Link>
              <Link href="/knowledge-base" className="block transition hover:text-[var(--text-primary)]">Knowledge base</Link>
              <Link href="/summaries" className="block transition hover:text-[var(--text-primary)]">Summaries</Link>
            </div>
          </div>
          <div>
            <p className="text-sm font-semibold text-[var(--text-primary)]">Resources</p>
            <div className="mt-4 space-y-3 text-sm text-[var(--text-secondary)]">
              <Link href="/settings" className="block transition hover:text-[var(--text-primary)]">Docs</Link>
              <a href="https://github.com/PritheevLingeswaran/rag-smart-qa" className="block transition hover:text-[var(--text-primary)]">GitHub</a>
              <span className="block">Contact placeholder</span>
            </div>
          </div>
          <div>
            <p className="text-sm font-semibold text-[var(--text-primary)]">Built with</p>
            <div className="mt-4 space-y-3 text-sm text-[var(--text-secondary)]">
              <span className="block">Next.js</span>
              <span className="block">FastAPI</span>
              <span className="block">Vector search + RAG</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
