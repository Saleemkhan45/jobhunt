import { Link } from "react-router-dom";
import { Bookmark, BookmarkCheck, MapPin, Clock, Building2 } from "lucide-react";
import { useApp } from "../context/AppContext";
import { jobTypeLabel, timeAgo } from "../lib/format";
import { Chip, SourceBadge } from "./Badges";

export default function JobCard({ job, index = 0 }) {
  const { trackedIds, saveJob } = useApp();
  const saved = trackedIds.has(job.fingerprint);
  const flat = job.description.replace(/\s+/g, " ").trim();
  const preview = flat.length > 170 ? `${flat.slice(0, 170).trimEnd()}…` : flat;

  return (
    <article
      className="animate-rise group relative flex flex-col rounded-2xl bg-card p-5 ring-1 ring-line transition hover:-translate-y-0.5 hover:shadow-lg hover:ring-teal/40"
      style={{ animationDelay: `${Math.min(index, 12) * 35}ms` }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-display text-lg font-semibold leading-snug text-ink">
            <Link to={`/jobs/${job.fingerprint}`} state={{ job }} className="after:absolute after:inset-0 focus:outline-none">
              {job.title}
            </Link>
          </h3>
          <p className="mt-1 flex items-center gap-1.5 text-sm text-muted">
            <Building2 size={14} className="shrink-0" /> <span className="truncate">{job.company}</span>
          </p>
        </div>
        <button
          type="button"
          onClick={() => !saved && saveJob(job)}
          className={`relative z-10 shrink-0 rounded-lg p-2 ring-1 transition ${
            saved ? "bg-teal text-white ring-teal" : "bg-white text-muted ring-line hover:text-teal hover:ring-teal"
          }`}
          aria-label={saved ? "Saved to tracker" : "Save to tracker"}
          title={saved ? "Saved to tracker" : "Save to tracker"}
        >
          {saved ? <BookmarkCheck size={18} /> : <Bookmark size={18} />}
        </button>
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {job.remote && <Chip tone="remote">Remote</Chip>}
        <Chip>{jobTypeLabel(job.job_type)}</Chip>
        {job.salary && <Chip tone="salary">{job.salary}</Chip>}
      </div>

      {preview && <p className="mt-3 line-clamp-2 text-sm leading-relaxed text-muted">{preview}</p>}

      <div className="mt-auto flex items-center justify-between gap-3 pt-4 text-xs text-muted">
        <span className="flex min-w-0 items-center gap-1.5">
          <MapPin size={13} className="shrink-0" /> <span className="truncate">{job.location}</span>
        </span>
        <span className="flex shrink-0 items-center gap-3">
          <span className="flex items-center gap-1"><Clock size={13} /> {timeAgo(job.posted_at)}</span>
          <SourceBadge source={job.source} />
        </span>
      </div>
    </article>
  );
}

export function JobCardSkeleton() {
  return (
    <div className="animate-pulse rounded-2xl bg-card p-5 ring-1 ring-line">
      <div className="h-5 w-3/4 rounded bg-line" />
      <div className="mt-2 h-4 w-1/3 rounded bg-line" />
      <div className="mt-4 flex gap-2">
        <div className="h-5 w-16 rounded bg-line" />
        <div className="h-5 w-20 rounded bg-line" />
      </div>
      <div className="mt-4 h-3 w-full rounded bg-line" />
      <div className="mt-2 h-3 w-5/6 rounded bg-line" />
    </div>
  );
}
