import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft, ExternalLink, Bookmark, BookmarkCheck, Building2, MapPin, Clock, Briefcase, Wallet, Globe, Hash,
} from "lucide-react";
import { useApp } from "../context/AppContext";
import { api } from "../lib/api";
import { SOURCE_INFO, formatDate, jobTypeLabel, timeAgo } from "../lib/format";
import { Chip, SourceBadge, StatusBadge } from "../components/Badges";

// "What you will do" / "Requirements:" -> a sub-heading. Short, one line, no sentence ending.
function isHeading(text) {
  return text.length <= 60 && !text.includes("\n") && !text.startsWith("•") && !/[.!?,]$/.test(text);
}

export default function JobPage() {
  const { id } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const { applications, trackedIds, saveJob } = useApp();

  const [job, setJob] = useState(location.state?.job ?? null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (job?.fingerprint === id) return;
    api.job(id).then(setJob).catch((err) => setError(err.message));
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 text-center">
        <h1 className="font-display text-2xl font-semibold">Job not found</h1>
        <p className="mt-2 text-muted">{error}</p>
        <Link to="/" className="mt-6 inline-block rounded-xl bg-ink px-5 py-3 font-semibold text-white">Back to search</Link>
      </div>
    );
  }
  if (!job) {
    return <div className="mx-auto max-w-5xl px-4 py-16 text-muted">Loading job…</div>;
  }

  const source = SOURCE_INFO[job.source] ?? { label: job.source, site: job.source };
  const tracked = applications.find((a) => a.id === job.fingerprint);
  const paragraphs = job.description.split(/\n{2,}/).filter(Boolean);

  const facts = [
    { icon: Building2, label: "Company", value: job.company },
    { icon: MapPin, label: "Location", value: job.location },
    { icon: Briefcase, label: "Job type", value: `${jobTypeLabel(job.job_type)}${job.remote ? " · Remote" : ""}` },
    { icon: Clock, label: "Posted", value: `${formatDate(job.posted_at)} (${timeAgo(job.posted_at)})` },
    { icon: Wallet, label: "Salary", value: job.salary || "Not listed" },
    { icon: Hash, label: "JobHunt ID", value: job.fingerprint },
  ];

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <button onClick={() => navigate(-1)} className="mb-6 inline-flex items-center gap-2 text-sm font-medium text-muted hover:text-teal">
        <ArrowLeft size={16} /> Back to results
      </button>

      <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
        <article className="animate-rise rounded-2xl bg-card p-6 ring-1 ring-line sm:p-8">
          <div className="flex flex-wrap items-center gap-2">
            <SourceBadge source={job.source} />
            {job.remote && <Chip tone="remote">Remote</Chip>}
            <Chip>{jobTypeLabel(job.job_type)}</Chip>
            {tracked && <StatusBadge status={tracked.status} />}
          </div>
          <h1 className="mt-4 font-display text-3xl font-bold leading-tight tracking-tight sm:text-4xl">{job.title}</h1>
          <p className="mt-2 text-lg text-muted">
            {job.company} · {job.location}
          </p>

          <div className="mt-6 flex flex-wrap gap-3">
            <a
              href={job.url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 rounded-xl bg-teal px-5 py-3 font-semibold text-white transition hover:bg-teal-dark"
            >
              Apply on {source.label} <ExternalLink size={16} />
            </a>
            {trackedIds.has(job.fingerprint) ? (
              <Link to="/tracker" className="inline-flex items-center gap-2 rounded-xl bg-white px-5 py-3 font-semibold text-teal ring-1 ring-teal">
                <BookmarkCheck size={18} /> In your tracker
              </Link>
            ) : (
              <button
                onClick={() => saveJob(job)}
                className="inline-flex items-center gap-2 rounded-xl bg-white px-5 py-3 font-semibold text-ink ring-1 ring-line transition hover:ring-teal hover:text-teal"
              >
                <Bookmark size={18} /> Save to tracker
              </button>
            )}
          </div>

          <hr className="my-8 border-line" />

          <h2 className="font-display text-xl font-semibold">Job description</h2>
          {paragraphs.length ? (
            <div className="mt-4 space-y-4 leading-relaxed text-[#2d3748]">
              {paragraphs.map((para, i) =>
                isHeading(para) ? (
                  <h3 key={i} className="pt-2 font-display text-lg font-semibold text-ink">{para}</h3>
                ) : (
                  <p key={i} className="whitespace-pre-line">{para}</p>
                ),
              )}
            </div>
          ) : (
            <p className="mt-4 text-muted">No description provided. Open the original post for details.</p>
          )}

          {job.tags.length > 0 && (
            <div className="mt-8 flex flex-wrap gap-2">
              {job.tags.map((tag) => (
                <span key={tag} className="rounded-full bg-paper px-3 py-1 text-sm text-muted ring-1 ring-line">#{tag}</span>
              ))}
            </div>
          )}
        </article>

        <aside className="space-y-4 lg:sticky lg:top-6 lg:self-start">
          <div className="rounded-2xl bg-card p-6 ring-1 ring-line">
            <h2 className="font-display text-lg font-semibold">Job details</h2>
            <dl className="mt-4 space-y-4">
              {facts.map(({ icon: Icon, label, value }) => (
                <div key={label} className="flex gap-3">
                  <Icon size={18} className="mt-0.5 shrink-0 text-teal" />
                  <div className="min-w-0">
                    <dt className="text-xs font-medium uppercase tracking-wide text-muted">{label}</dt>
                    <dd className="break-words text-sm text-ink">{value}</dd>
                  </div>
                </div>
              ))}
            </dl>
          </div>
          <div className="rounded-2xl bg-ink p-6 text-white">
            <p className="flex items-center gap-2 text-sm font-semibold text-mint">
              <Globe size={16} /> Where this job comes from
            </p>
            <p className="mt-2 text-sm text-slate-300">
              This listing was fetched live from <b className="text-white">{source.site}</b>. The original page has the employer’s application form.
            </p>
            <a href={job.url} target="_blank" rel="noreferrer" className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-mint hover:underline">
              Open original post <ExternalLink size={14} />
            </a>
          </div>
        </aside>
      </div>
    </div>
  );
}
