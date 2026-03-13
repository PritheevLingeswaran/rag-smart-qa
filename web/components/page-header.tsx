export function PageHeader({
  eyebrow,
  title,
  description,
  actions
}: {
  eyebrow: string;
  title: string;
  description: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">{eyebrow}</p>
        <h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">{title}</h2>
        <p className="mt-2 max-w-2xl text-sm text-slate-600">{description}</p>
      </div>
      {actions}
    </div>
  );
}
