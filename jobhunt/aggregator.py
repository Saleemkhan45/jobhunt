"""Runs every job board concurrently and merges the results.

`asyncio.gather` fires all requests at once, so total time is roughly the
slowest board, not the sum of all boards. `return_exceptions=True` means one
board being down never breaks the whole search.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from itertools import chain
from pathlib import Path

import aiohttp

from .config import Settings
from .decorators import timer
from .models import Job, SearchQuery
from .pipeline import run_pipeline
from .sources import ALL_SOURCES, JobSource, SourceError

logger = logging.getLogger("jobhunt")


@dataclass
class SearchResult:
    query: SearchQuery
    jobs: list[Job]
    per_source: dict[str, int] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)
    raw_total: int = 0

    @property
    def duplicates_removed(self) -> int:
        return max(self.raw_total - len(self.jobs), 0)


class JobAggregator:
    def __init__(self, settings: Settings, source_names: list[str] | None = None) -> None:
        unknown = set(source_names or []) - ALL_SOURCES.keys()
        if unknown:
            raise ValueError(f"unknown source(s): {', '.join(sorted(unknown))}")
        self._settings = settings
        self._source_names = source_names or list(ALL_SOURCES)

    def _build_sources(self, session: aiohttp.ClientSession | None) -> list[JobSource]:
        fixtures: Path | None = self._settings.fixture_dir if self._settings.offline else None
        return [ALL_SOURCES[name](session=session, fixture_dir=fixtures) for name in self._source_names]

    @timer
    async def search(self, query: SearchQuery) -> SearchResult:
        timeout = aiohttp.ClientTimeout(total=self._settings.timeout_seconds)
        headers = {"User-Agent": self._settings.user_agent, "Accept": "application/json"}

        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            sources = self._build_sources(session)
            outcomes = await asyncio.gather(
                *(source.fetch(query) for source in sources), return_exceptions=True
            )

        batches: list[list[Job]] = []
        result = SearchResult(query=query, jobs=[])
        for source, outcome in zip(sources, outcomes):
            if isinstance(outcome, BaseException):
                message = str(outcome) if isinstance(outcome, SourceError) else repr(outcome)
                result.errors[source.name] = message
                logger.warning("source %s failed: %s", source.name, message)
                continue
            batches.append(outcome)
            result.per_source[source.name] = len(outcome)

        # Newest first across all boards, then the lazy generator pipeline.
        merged = sorted(
            chain.from_iterable(batches),
            key=lambda job: job.posted_at.timestamp() if job.posted_at else 0,
            reverse=True,
        )
        matching = [job for job in merged if job.matches(query.keyword)]
        result.raw_total = len(matching)
        result.jobs = list(run_pipeline(merged, query))
        return result
