import { cn } from "@/lib/utils";

export function StatCard({
  label,
  value,
  subtext,
  icon,
  trend,
  className
}: {
  label: string;
  value: string | number;
  subtext: string;
  icon?: React.ReactNode;
  trend?: string;
  className?: string;
}) {
  return (
    <div className={cn("panel panel-hover premium-ring min-h-[240px] overflow-hidden p-5", className)}>
      <div className="flex items-start justify-between">
        <div>
          <p className="metric-label">{label}</p>
          <p className="mt-4 text-4xl font-semibold tracking-tight text-[var(--text-primary)]">{value}</p>
        </div>
        {icon ? (
          <div className="icon-chip">{icon}</div>
        ) : null}
      </div>
      <p className="mt-4 text-sm leading-6 text-[var(--text-secondary)]">{subtext}</p>
      {trend ? (
        <p className="mt-3 text-xs uppercase tracking-[0.22em] text-[var(--primary)]">{trend}</p>
      ) : null}
    </div>
  );
}
