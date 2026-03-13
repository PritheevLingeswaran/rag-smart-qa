import type { SummaryPayload } from "@/types/api";

export function SummaryCard({ summary }: { summary?: SummaryPayload | null }) {
  if (!summary) {
    return <div className="panel p-5 text-sm text-slate-500">Summary not generated yet.</div>;
  }

  return (
    <div className="panel space-y-5 p-5">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Summary</p>
        <h3 className="mt-2 text-xl font-semibold text-slate-950">{summary.title ?? "Document summary"}</h3>
        <p className="mt-3 text-sm leading-7 text-slate-700">{summary.summary}</p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="panel-muted p-4">
          <p className="text-sm font-medium text-slate-900">Key insights</p>
          <ul className="mt-3 space-y-2 text-sm text-slate-600">
            {summary.key_insights.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
        <div className="panel-muted p-4">
          <p className="text-sm font-medium text-slate-900">Important points</p>
          <ul className="mt-3 space-y-2 text-sm text-slate-600">
            {summary.important_points.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
