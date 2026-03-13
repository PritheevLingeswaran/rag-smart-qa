"use client";

import { useQuery } from "@tanstack/react-query";

import { PageHeader } from "@/components/page-header";
import { api } from "@/lib/api";

export default function SettingsPage() {
  const settingsQuery = useQuery({ queryKey: ["settings"], queryFn: api.settings });
  const settings = settingsQuery.data;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Settings"
        title="Runtime configuration"
        description="A read-only view of the API models, feature flags, and retrieval defaults exposed by the backend."
      />
      <div className="grid gap-4 md:grid-cols-2">
        {[
          ["Environment", settings?.environment],
          ["Generation model", settings?.default_generation_model],
          ["Embedding model", settings?.default_embedding_model],
          ["Vector store", settings?.vector_store_provider],
          ["Default retrieval", settings?.default_retrieval_mode],
          ["Auth", settings?.auth_enabled ? settings?.auth_provider : "disabled"],
          ["Summaries", settings?.summaries_enabled ? "enabled" : "disabled"]
        ].map(([label, value]) => (
          <div key={label} className="panel p-5">
            <p className="text-sm text-slate-500">{label}</p>
            <p className="mt-3 text-lg font-semibold text-slate-950">{value ?? "loading..."}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
