import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { AlertTriangle, Layers, SearchX } from "lucide-react";
import SearchForm from "../components/SearchForm";
import JobCard, { JobCardSkeleton } from "../components/JobCard";
import { SourceBadge } from "../components/Badges";
import { api } from "../lib/api";

const PAGE_SIZE = 30;
const QUICK_PICKS = ["python", "react", "node.js", "intern", "data analyst", "django"];
const cache = new Map(); // keeps results when you go to a job and come back

function paramsToForm(params) {
  return {
    keyword: params.get("keyword") ?? "",
    location: params.get("location") ?? "",
    job_type: params.get("job_type") ?? "",
    days: params.get("days") ?? "",
    remote: params.get("remote") === "true",
    offline: params.get("offline") === "true",
  };
}

export default function SearchPage() {
  const [params, setParams] = useSearchParams();
  const form = useMemo(() => paramsToForm(params), [params]);
  const limit = Number(params.get("limit")) || PAGE_SIZE;
  const key = params.toString();

  const [result, setResult] = useState(() => cache.get(key) ?? null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!form.keyword) {
      setResult(null);
      return;
    }
    if (cache.has(key)) {
      setResult(cache.get(key));
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError("");
    api
      .search({ ...form, limit })
      .then((data) => {
        if (cancelled) return;
        cache.set(key, data);
        setResult(data);
      })
      .catch((err) => !cancelled && setError(err.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [key]); // eslint-disable-line react-hooks/exhaustive-deps

  const runSearch = (values) => {
    const next = new URLSearchParams();
    Object.entries(values).forEach(([k, v]) => v && next.set(k, String(v)));
    setParams(next);
  };

  const loadMore = () => {
    const next = new URLSearchParams(params);
    next.set("limit", String(limit + PAGE_SIZE));
    setParams(next, { replace: true });
  };

  const fetched = result ? Object.values(result.per_source).reduce((a, b) => a + b, 0) : 0;
  const allFailed = result && Object.keys(result.per_source).length === 0;

  return (
    <>
      <section className="bg-ink pb-10 pt-10 text-white sm:pt-14">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <p className="text-sm font-semibold uppercase tracking-[0.14em] text-mint">One search · three job boards</p>
          <h1 className="mt-3 max-w-3xl font-display text-4xl font-bold leading-tight tracking-tight sm:text-5xl">
            Find jobs and internships without opening ten tabs.
          </h1>
          <p className="mt-3 max-w-2xl text-slate-300">
            JobHunt searches Arbeitnow, Remotive and Himalayas at the same time, removes duplicates and shows the newest jobs first.
          </p>
          <div className="mt-8">
            <SearchForm initial={form} onSearch={runSearch} loading={loading} />
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        {!form.keyword && (
          <div className="rounded-2xl bg-card p-8 text-center ring-1 ring-line">
            <Layers className="mx-auto text-teal" size={36} />
            <h2 className="mt-3 font-display text-2xl font-semibold">Start with a skill or job title</h2>
            <p className="mt-1 text-muted">Try one of these:</p>
            <div className="mt-4 flex flex-wrap justify-center gap-2">
              {QUICK_PICKS.map((word) => (
                <button
                  key={word}
                  onClick={() => runSearch({ ...form, keyword: word })}
                  className="rounded-full bg-white px-4 py-2 text-sm font-medium ring-1 ring-line transition hover:text-teal hover:ring-teal"
                >
                  {word}
                </button>
              ))}
            </div>
          </div>
        )}

        {error && (
          <div className="flex items-start gap-3 rounded-xl bg-rose-50 p-4 text-rose-900 ring-1 ring-rose-200">
            <AlertTriangle size={20} className="mt-0.5 shrink-0" />
            <div>
              <p className="font-semibold">Search failed</p>
              <p className="text-sm">{error}</p>
            </div>
          </div>
        )}

        {result && !loading && (
          <>
            <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="font-display text-2xl font-semibold">
                  {result.jobs.length} {result.jobs.length === 1 ? "job" : "jobs"} for “{result.query.keyword}”
                </h2>
                <p className="text-sm text-muted">
                  {fetched} listings fetched · {result.matched} matched · duplicates removed
                  {result.offline && " · demo data"}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                {Object.entries(result.per_source).map(([name, count]) => (
                  <span key={name} className="flex items-center gap-1.5 text-sm text-muted">
                    <SourceBadge source={name} /> {count}
                  </span>
                ))}
              </div>
            </div>

            {Object.entries(result.errors).map(([name, message]) => (
              <div key={name} className="mb-3 flex items-start gap-2 rounded-xl bg-amber-50 p-3 text-sm text-amber-900 ring-1 ring-amber-200">
                <AlertTriangle size={16} className="mt-0.5 shrink-0" />
                <span>
                  <b className="capitalize">{name}</b> is unavailable right now. Showing results from the other boards. <span className="opacity-70">({message})</span>
                </span>
              </div>
            ))}
            {allFailed && (
              <p className="mb-4 text-sm text-muted">Tip: tick “Demo data (offline)” to try JobHunt without internet.</p>
            )}

            {result.jobs.length === 0 && !allFailed ? (
              <div className="rounded-2xl bg-card p-10 text-center ring-1 ring-line">
                <SearchX className="mx-auto text-muted" size={36} />
                <h3 className="mt-3 font-display text-xl font-semibold">No jobs match these filters</h3>
                <p className="mt-1 text-muted">Try a broader keyword, remove the location, or allow older posts.</p>
              </div>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {result.jobs.map((job, i) => (
                  <JobCard key={job.fingerprint} job={job} index={i} />
                ))}
              </div>
            )}

            {result.jobs.length >= limit && result.matched > result.jobs.length && (
              <div className="mt-8 text-center">
                <button onClick={loadMore} className="rounded-xl bg-ink px-6 py-3 font-semibold text-white transition hover:bg-ink-soft">
                  Show more jobs
                </button>
              </div>
            )}
          </>
        )}

        {loading && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }, (_, i) => (
              <JobCardSkeleton key={i} />
            ))}
          </div>
        )}
      </section>
    </>
  );
}
