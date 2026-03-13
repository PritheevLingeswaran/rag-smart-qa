"use client";

import { BrainCircuit, ChevronRight, Github, Mail, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/components/auth-provider";
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
      title: "Session ready",
      description: "Entering your intelligence workspace."
    });
    router.replace("/workspace");
  }

  return (
    <div className="min-h-screen overflow-hidden px-6 py-10">
      <div className="mx-auto flex max-w-7xl items-center justify-between">
        <Link href="/" className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-[#3B82F6] via-[#6366F1] to-[#8B5CF6]">
            <BrainCircuit className="h-5 w-5 text-white" />
          </div>
          <span className="text-lg font-extrabold tracking-tight">
            rag<span className="text-indigo-400">smart</span>qa
          </span>
        </Link>
      </div>

      <div className="relative mx-auto mt-12 grid min-h-[calc(100vh-8rem)] max-w-6xl items-center gap-12 lg:grid-cols-[0.95fr_1.05fr]">
        <section className="panel rounded-[2.5rem] p-10 md:p-12">
          <div className="flex justify-between">
            {[1, 2, 3].map((step) => (
              <div key={step} className="flex flex-col items-center gap-3">
                <div className={`flex h-10 w-10 items-center justify-center rounded-full ${step === 1 ? "bg-indigo-500 text-white" : "border border-white/10 bg-white/5 text-slate-500"}`}>
                  <span className="text-sm font-black">{step}</span>
                </div>
                <span className={`text-[10px] font-bold uppercase tracking-[0.22em] ${step === 1 ? "text-white" : "text-slate-600"}`}>
                  {step === 1 ? "Account" : step === 2 ? "Organization" : "Flow settings"}
                </span>
              </div>
            ))}
          </div>

          <div className="mt-12">
            <h1 className="text-4xl font-black italic tracking-tight">Get Started.</h1>
            <p className="mt-3 text-sm text-slate-400">
              Create your secure gateway to document intelligence.
            </p>

            <div className="mt-8 grid grid-cols-2 gap-4">
              <button className="surface-card flex items-center justify-center gap-3 py-4 text-sm font-black">
                <Mail className="h-4 w-4" />
                Google
              </button>
              <button className="surface-card flex items-center justify-center gap-3 py-4 text-sm font-black">
                <Github className="h-4 w-4" />
                GitHub
              </button>
            </div>

            <div className="relative my-8">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-white/5" />
              </div>
              <div className="relative flex justify-center">
                <span className="bg-[var(--bg-primary)] px-4 text-xs font-bold uppercase tracking-[0.22em] text-slate-500">
                  Or with email
                </span>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-2">
                <label className="ml-1 text-xs font-bold uppercase tracking-[0.2em] text-slate-500">
                  Display name
                </label>
                <input
                  value={displayName}
                  onChange={(event) => setDisplayName(event.target.value)}
                  placeholder="Pritheev"
                  className="w-full rounded-[1.35rem] border border-white/10 bg-white/5 px-5 py-4 text-sm outline-none transition placeholder:text-slate-700 focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10"
                />
              </div>
              <div className="space-y-2">
                <label className="ml-1 text-xs font-bold uppercase tracking-[0.2em] text-slate-500">
                  Work email
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="alex@company.com"
                  className="w-full rounded-[1.35rem] border border-white/10 bg-white/5 px-5 py-4 text-sm outline-none transition placeholder:text-slate-700 focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10"
                />
              </div>
              <div className="space-y-2">
                <label className="ml-1 text-xs font-bold uppercase tracking-[0.2em] text-slate-500">
                  Choose password
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Enter any password for local mode"
                  className="w-full rounded-[1.35rem] border border-white/10 bg-white/5 px-5 py-4 text-sm outline-none transition placeholder:text-slate-700 focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10"
                />
              </div>
              <button type="submit" className="btn-primary w-full justify-center gap-3 py-4 text-sm">
                Create account
                <ChevronRight className="h-5 w-5" />
              </button>
            </form>
          </div>
        </section>

        <section className="panel premium-ring rounded-[2.5rem] p-10 md:p-12">
          <div className="inline-flex items-center gap-2 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-3 py-1 text-xs font-bold uppercase tracking-[0.24em] text-indigo-300">
            Onboarding flow
          </div>
          <h2 className="mt-6 text-4xl font-black leading-tight">
            Join the <span className="text-gradient">flow.</span>
          </h2>
          <p className="mt-5 max-w-xl text-base leading-7 text-slate-400">
            This auth experience now follows the onboarding reference you shared instead of the previous web page design.
          </p>

          <div className="mt-10 grid gap-4">
            {[
              "Create a workspace identity",
              "Route `x-user-id` cleanly into the backend",
              "Preserve a future upgrade path for real auth providers"
            ].map((item) => (
              <div key={item} className="surface-card flex items-start gap-3 p-4">
                <ShieldCheck className="mt-0.5 h-5 w-5 text-indigo-300" />
                <p className="text-sm leading-7 text-slate-300">{item}</p>
              </div>
            ))}
          </div>

          <Link href="/" className="mt-8 inline-flex items-center gap-2 text-sm font-bold text-slate-400 transition hover:text-white">
            Back to landing page
          </Link>
        </section>
      </div>
    </div>
  );
}
