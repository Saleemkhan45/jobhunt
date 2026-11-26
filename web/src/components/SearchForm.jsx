import { useEffect, useState } from "react";
import { Search, MapPin, SlidersHorizontal, FlaskConical } from "lucide-react";
import { JOB_TYPES } from "../lib/format";

const AGE_OPTIONS = [
  { value: "", label: "Any time" },
  { value: "1", label: "Last 24 hours" },
  { value: "7", label: "Last 7 days" },
  { value: "14", label: "Last 14 days" },
  { value: "30", label: "Last 30 days" },
];

export default function SearchForm({ initial, onSearch, loading }) {
  const [form, setForm] = useState(initial);
  useEffect(() => setForm(initial), [initial]);

  const set = (key) => (event) =>
    setForm((f) => ({ ...f, [key]: event.target.type === "checkbox" ? event.target.checked : event.target.value }));

  const submit = (event) => {
    event.preventDefault();
    onSearch(form);
  };

  const fieldClass =
    "w-full rounded-xl border-0 bg-white py-3 text-ink ring-1 ring-line placeholder:text-slate-400 focus:ring-2 focus:ring-teal focus:outline-none";

  return (
    <form onSubmit={submit} className="rounded-2xl bg-white/5 p-3 ring-1 ring-white/10 backdrop-blur sm:p-4">
      <div className="grid gap-3 md:grid-cols-[1.4fr_1fr_auto]">
        <label className="relative block">
          <span className="sr-only">Keyword</span>
          <Search size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            value={form.keyword}
            onChange={set("keyword")}
            placeholder="Job title or skill, e.g. python, react, intern"
            className={`${fieldClass} pl-10 pr-3`}
            minLength={2}
            maxLength={60}
            required
          />
        </label>
        <label className="relative block">
          <span className="sr-only">Location</span>
          <MapPin size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            value={form.location}
            onChange={set("location")}
            placeholder="City or country (optional)"
            className={`${fieldClass} pl-10 pr-3`}
            maxLength={60}
          />
        </label>
        <button
          type="submit"
          disabled={loading}
          className="rounded-xl bg-mint px-6 py-3 font-semibold text-ink transition hover:bg-[#7ee0cc] disabled:cursor-wait disabled:opacity-70"
        >
          {loading ? "Searching…" : "Search jobs"}
        </button>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-slate-200">
        <span className="flex items-center gap-1.5 text-slate-400">
          <SlidersHorizontal size={15} /> Filters
        </span>
        <select value={form.job_type} onChange={set("job_type")} className="rounded-lg border-0 bg-white/10 px-2.5 py-1.5 text-white ring-1 ring-white/15 focus:ring-mint">
          {JOB_TYPES.map((t) => (
            <option key={t.value} value={t.value} className="text-ink">{t.label}</option>
          ))}
        </select>
        <select value={form.days} onChange={set("days")} className="rounded-lg border-0 bg-white/10 px-2.5 py-1.5 text-white ring-1 ring-white/15 focus:ring-mint">
          {AGE_OPTIONS.map((t) => (
            <option key={t.value} value={t.value} className="text-ink">{t.label}</option>
          ))}
        </select>
        <label className="flex cursor-pointer items-center gap-2">
          <input type="checkbox" checked={form.remote} onChange={set("remote")} className="h-4 w-4 accent-[#5fd3bc]" />
          Remote only
        </label>
        <label className="flex cursor-pointer items-center gap-2" title="Use bundled sample data, works without internet">
          <input type="checkbox" checked={form.offline} onChange={set("offline")} className="h-4 w-4 accent-[#5fd3bc]" />
          <FlaskConical size={15} /> Demo data (offline)
        </label>
      </div>
    </form>
  );
}
