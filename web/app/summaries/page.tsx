"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { PageHeader } from "@/components/page-header";
import { api } from "@/lib/api";

export default function SummariesPage() {
  const documentsQuery = useQuery({ queryKey: ["documents"], queryFn: api.documents });
  const summaryDocs = (documentsQuery.data?.documents ?? []).filter(
    (document) => document.summary_status !== "disabled"
  );

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Summaries"
        title="Cached document briefings"
        description="Summaries, insights, and important points are stored per document so users can skim before asking questions."
      />
      <div className="grid gap-4 md:grid-cols-2">
        {summaryDocs.map((document) => (
          <Link key={document.id} href={`/documents/${document.id}`} className="panel p-5">
            <p className="text-sm text-slate-500">{document.file_type.toUpperCase()}</p>
            <h3 className="mt-2 text-xl font-semibold text-slate-950">{document.filename}</h3>
            <p className="mt-3 text-sm text-slate-600">
              Summary status: {document.summary_status} • Indexing status: {document.indexing_status}
            </p>
          </Link>
        ))}
      </div>
    </div>
  );
}
