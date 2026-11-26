"""Generator pipeline: filter, de-duplicate and cap results lazily.

Each stage pulls one job at a time from the stage before it, so nothing is
copied into intermediate lists. `take()` stops the whole chain early once we
have enough results.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from datetime import datetime, timedelta, timezone

from .models import Job, SearchQuery


def match_keyword(jobs: Iterable[Job], keyword: str) -> Iterator[Job]:
    for job in jobs:
        if job.matches(keyword):
            yield job


def match_location(jobs: Iterable[Job], location: str | None) -> Iterator[Job]:
    for job in jobs:
        if not location or location.lower() in job.location.lower() or job.remote:
            yield job


def only_remote(jobs: Iterable[Job], enabled: bool) -> Iterator[Job]:
    yield from (job for job in jobs if not enabled or job.remote)


def match_job_type(jobs: Iterable[Job], job_type) -> Iterator[Job]:  # noqa: ANN001
    yield from (job for job in jobs if job_type is None or job.job_type == job_type)


def newer_than(jobs: Iterable[Job], days: int | None) -> Iterator[Job]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days) if days else None
    for job in jobs:
        if cutoff is None or job.posted_at is None or job.posted_at >= cutoff:
            yield job


def deduplicate(jobs: Iterable[Job]) -> Iterator[Job]:
    """Skip a job if the same title + company was already yielded by any source."""
    seen: set[str] = set()
    for job in jobs:
        if job.fingerprint not in seen:
            seen.add(job.fingerprint)
            yield job


def take(jobs: Iterable[Job], limit: int) -> Iterator[Job]:
    if limit <= 0:
        return
    for count, job in enumerate(jobs, start=1):
        yield job
        if count >= limit:
            return  # stop before pulling one more item from upstream


def run_pipeline(jobs: Iterable[Job], query: SearchQuery) -> Iterator[Job]:
    """Chain every stage. Still lazy: nothing runs until the caller iterates."""
    stream = match_keyword(jobs, query.keyword)
    stream = match_location(stream, query.location)
    stream = only_remote(stream, query.remote_only)
    stream = match_job_type(stream, query.job_type)
    stream = newer_than(stream, query.max_age_days)
    stream = deduplicate(stream)
    return take(stream, query.limit)


def batched(items: Iterable[Job], size: int) -> Iterator[list[Job]]:
    """Yield jobs in pages of `size` (used for paged terminal output)."""
    batch: list[Job] = []
    for item in items:
        batch.append(item)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch
