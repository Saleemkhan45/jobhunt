export const JOB_TYPES = [
  { value: "", label: "Any type" },
  { value: "full_time", label: "Full time" },
  { value: "part_time", label: "Part time" },
  { value: "internship", label: "Internship" },
  { value: "contract", label: "Contract" },
  { value: "freelance", label: "Freelance" },
];

export const STATUSES = [
  { value: "saved", label: "Saved", tone: "bg-sky-50 text-sky-800 ring-sky-200" },
  { value: "applied", label: "Applied", tone: "bg-indigo-50 text-indigo-800 ring-indigo-200" },
  { value: "interview", label: "Interview", tone: "bg-amber-50 text-amber-800 ring-amber-200" },
  { value: "offer", label: "Offer", tone: "bg-fuchsia-50 text-fuchsia-800 ring-fuchsia-200" },
  { value: "selected", label: "Selected", tone: "bg-emerald-50 text-emerald-800 ring-emerald-200" },
  { value: "rejected", label: "Rejected", tone: "bg-rose-50 text-rose-800 ring-rose-200" },
];

export const SOURCE_INFO = {
  arbeitnow: { label: "Arbeitnow", site: "arbeitnow.com", dot: "bg-orange-500" },
  remotive: { label: "Remotive", site: "remotive.com", dot: "bg-sky-500" },
  himalayas: { label: "Himalayas", site: "himalayas.app", dot: "bg-violet-500" },
};

export function jobTypeLabel(value) {
  return JOB_TYPES.find((t) => t.value === value)?.label ?? "Other";
}

export function statusInfo(value) {
  return STATUSES.find((s) => s.value === value) ?? STATUSES[0];
}

export function timeAgo(iso) {
  if (!iso) return "Date unknown";
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
  if (days <= 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 30) return `${days} days ago`;
  const months = Math.floor(days / 30);
  return months === 1 ? "1 month ago" : `${months} months ago`;
}

export function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}
