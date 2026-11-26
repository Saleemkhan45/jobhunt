import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Trash2, ArrowRight, Inbox, StickyNote } from "lucide-react";
import { useApp } from "../context/AppContext";
import { api } from "../lib/api";
import { STATUSES, statusInfo, timeAgo } from "../lib/format";
import { SourceBadge } from "../components/Badges";

function Stat({ label, value, hint }) {
  return (
    <div className="rounded-2xl bg-card p-5 ring-1 ring-line">
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-1 font-display text-3xl font-bold">{value}</p>
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
    </div>
  );
}

function ApplicationCard({ app }) {
  const { transitions, moveTo, remove } = useApp();
  const [note, setNote] = useState("");
  const [showNote, setShowNote] = useState(false);
  const nextSteps = transitions[app.status] ?? [];
  const last = app.history[app.history.length - 1];
  const lastNote = [...app.history].reverse().find((h) => h.note)?.note;

  const move = async (status) => {
    await moveTo(app.id, status, note);
    setNote("");
    setShowNote(false);
  };

  return (
    <div className="animate-rise rounded-xl bg-white p-4 ring-1 ring-line">
      <div className="flex items-start justify-between gap-2">
        <Link to={`/jobs/${app.id}`} state={{ job: app.job }} className="font-semibold leading-snug hover:text-teal">
          {app.job.title}
        </Link>
        <button
          onClick={() => window.confirm(`Remove “${app.job.title}” from your tracker?`) && remove(app.id)}
          className="shrink-0 rounded-md p-1 text-slate-400 hover:bg-rose-50 hover:text-rose-700"
          aria-label="Remove from tracker"
        >
          <Trash2 size={16} />
        </button>
      </div>
      <p className="mt-1 text-sm text-muted">{app.job.company}</p>
      <div className="mt-3 flex items-center justify-between text-xs text-muted">
        <SourceBadge source={app.job.source} />
        <span>Updated {timeAgo(last.at).toLowerCase()}</span>
      </div>
      {lastNote && (
        <p className="mt-3 flex items-start gap-1.5 rounded-lg bg-paper p-2 text-xs text-muted">
          <StickyNote size={13} className="mt-0.5 shrink-0" /> {lastNote}
        </p>
      )}

      {nextSteps.length > 0 && (
        <div className="mt-3 border-t border-line pt-3">
          {showNote ? (
            <input
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Note, e.g. interview Friday 3pm"
              maxLength={300}
              className="mb-2 w-full rounded-lg border-0 px-2.5 py-1.5 text-sm ring-1 ring-line focus:ring-2 focus:ring-teal focus:outline-none"
            />
          ) : (
            <button onClick={() => setShowNote(true)} className="mb-2 text-xs font-medium text-teal hover:underline">
              + Add a note
            </button>
          )}
          <div className="flex flex-wrap gap-1.5">
            {nextSteps.map((status) => (
              <button
                key={status}
                onClick={() => move(status)}
                className={`inline-flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-semibold ring-1 transition hover:brightness-95 ${statusInfo(status).tone}`}
              >
                <ArrowRight size={12} /> {statusInfo(status).label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function TrackerPage() {
  const { applications } = useApp();
  const [report, setReport] = useState(null);

  useEffect(() => {
    api.report().then(setReport).catch(() => setReport(null));
  }, [applications]);

  const counts = report?.by_status ?? {};
  const appliedOrLater = ["applied", "interview", "offer", "selected", "rejected"].reduce((n, s) => n + (counts[s] ?? 0), 0);

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <p className="text-sm font-semibold uppercase tracking-[0.14em] text-teal">Application tracker</p>
      <h1 className="mt-2 font-display text-3xl font-bold tracking-tight sm:text-4xl">Your job search, in one place</h1>
      <p className="mt-2 max-w-2xl text-muted">
        Move each job through the stages. JobHunt only allows real next steps, so a rejected job can’t jump back to interview.
      </p>

      <div className="mt-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Jobs tracked" value={report?.total_tracked ?? applications.length} />
        <Stat label="Applied or further" value={appliedOrLater} />
        <Stat label="Interviews" value={(counts.interview ?? 0) + (counts.offer ?? 0) + (counts.selected ?? 0)} />
        <Stat label="Interview rate" value={`${report?.interview_rate ?? 0}%`} hint="interviews ÷ applications" />
      </div>

      {applications.length === 0 ? (
        <div className="mt-8 rounded-2xl bg-card p-10 text-center ring-1 ring-line">
          <Inbox className="mx-auto text-teal" size={36} />
          <h2 className="mt-3 font-display text-xl font-semibold">Nothing tracked yet</h2>
          <p className="mt-1 text-muted">Search for jobs and click the bookmark icon to save them here.</p>
          <Link to="/" className="mt-5 inline-block rounded-xl bg-ink px-5 py-3 font-semibold text-white">Find jobs</Link>
        </div>
      ) : (
        <div className="mt-8 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {STATUSES.map((column) => {
            const items = applications.filter((a) => a.status === column.value);
            return (
              <section key={column.value} className="rounded-2xl bg-paper/60 p-3 ring-1 ring-line">
                <header className="mb-3 flex items-center justify-between px-1">
                  <h2 className="font-display font-semibold">{column.label}</h2>
                  <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ring-1 ${column.tone}`}>{items.length}</span>
                </header>
                <div className="space-y-3">
                  {items.length ? items.map((app) => <ApplicationCard key={app.id} app={app} />) : (
                    <p className="rounded-xl border border-dashed border-line p-4 text-center text-sm text-slate-400">No jobs here</p>
                  )}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}
