export function StatCard({
  label,
  value,
  subtext
}: {
  label: string;
  value: string | number;
  subtext: string;
}) {
  return (
    <div className="panel p-5">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-4 text-3xl font-semibold text-slate-950">{value}</p>
      <p className="mt-2 text-sm text-slate-500">{subtext}</p>
    </div>
  );
}
