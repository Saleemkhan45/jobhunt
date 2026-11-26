import { SOURCE_INFO, statusInfo } from "../lib/format";

export function SourceBadge({ source }) {
  const info = SOURCE_INFO[source] ?? { label: source, dot: "bg-slate-400" };
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-white px-2.5 py-1 text-xs font-medium text-muted ring-1 ring-line">
      <span className={`h-2 w-2 rounded-full ${info.dot}`} aria-hidden="true" />
      {info.label}
    </span>
  );
}

export function StatusBadge({ status }) {
  const info = statusInfo(status);
  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${info.tone}`}>
      {info.label}
    </span>
  );
}

export function Chip({ children, tone = "default" }) {
  const tones = {
    default: "bg-paper text-muted ring-line",
    remote: "bg-emerald-50 text-emerald-800 ring-emerald-200",
    salary: "bg-amber-50 text-amber-900 ring-amber-200",
  };
  return (
    <span className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium ring-1 ${tones[tone]}`}>
      {children}
    </span>
  );
}
