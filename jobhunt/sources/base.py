"""Abstract base class every job board implements.

OOP in one place:
- Abstraction:   `JobSource` defines *what* a source does (build request, parse
                 one raw item) without saying *how*.
- Inheritance:   Arbeitnow/Remotive/Himalayas subclass it and reuse fetching,
                 retrying, validation and offline mode for free.
- Polymorphism:  the aggregator calls `source.fetch(query)` on any source and
                 each one parses its own JSON format.
- Encapsulation: the HTTP session, stats and skipped-item counter are kept
                 private (`_session`, `_stats`) and exposed read-only.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

import aiohttp
from pydantic import ValidationError

from ..decorators import log_call, rate_limit, retry, timer
from ..models import Job, SearchQuery

logger = logging.getLogger("jobhunt")


class SourceError(Exception):
    """Raised when a source cannot be reached or returns bad data."""


class JobSource(ABC):
    name: str = "base"
    base_url: str = ""

    def __init__(
        self,
        session: aiohttp.ClientSession | None = None,
        fixture_dir: Path | None = None,
    ) -> None:
        self._session = session
        self._fixture_dir = fixture_dir
        self._stats = {"raw": 0, "valid": 0, "skipped": 0}

    # ---- the two methods each subclass must provide -------------------------

    @abstractmethod
    def build_params(self, query: SearchQuery) -> dict[str, Any]:
        """Query-string parameters for this API."""

    @abstractmethod
    def extract_items(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Pull the list of raw job dicts out of the API's envelope."""

    @abstractmethod
    def to_job(self, raw: dict[str, Any]) -> Job:
        """Map one raw dict into a validated `Job` (may raise ValidationError)."""

    # ---- shared behaviour ----------------------------------------------------

    @property
    def stats(self) -> dict[str, int]:
        return dict(self._stats)  # a copy: callers cannot change our counters

    @property
    def is_offline(self) -> bool:
        return self._fixture_dir is not None

    @retry(attempts=3, base_delay=0.5, exceptions=(aiohttp.ClientError, TimeoutError))
    @rate_limit(calls_per_second=2)
    async def _get_json(self, params: dict[str, Any]) -> dict[str, Any]:
        if self._session is None:
            raise SourceError(f"{self.name}: no HTTP session")
        async with self._session.get(self.base_url, params=params) as response:
            if response.status == 429:
                raise aiohttp.ClientResponseError(
                    response.request_info, (), status=429, message="rate limited"
                )
            response.raise_for_status()
            return await response.json(content_type=None)

    def _load_fixture(self) -> dict[str, Any]:
        path = self._fixture_dir / f"{self.name}.json"  # type: ignore[operator]
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)

    def parse(self, payload: dict[str, Any]) -> Iterator[Job]:
        """Generator: validate items one by one, skipping (not crashing on) bad ones."""
        for raw in self.extract_items(payload):
            self._stats["raw"] += 1
            try:
                job = self.to_job(raw)
            except (ValidationError, KeyError, TypeError, ValueError) as exc:
                self._stats["skipped"] += 1
                logger.debug("%s: skipped invalid item (%s)", self.name, str(exc)[:120])
                continue
            self._stats["valid"] += 1
            yield job

    @timer
    @log_call
    async def fetch(self, query: SearchQuery) -> list[Job]:
        """Fetch + validate jobs for this query. Offline mode reads a JSON fixture."""
        try:
            if self.is_offline:
                payload = self._load_fixture()
            else:
                payload = await self._get_json(self.build_params(query))
        except (aiohttp.ClientError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise SourceError(f"{self.name}: {exc.__class__.__name__}: {exc}") from exc
        return list(self.parse(payload))

    async def stream(self, query: SearchQuery) -> AsyncIterator[Job]:
        """Async generator version of `fetch` for callers that want items as they come."""
        for job in await self.fetch(query):
            yield job

    def __repr__(self) -> str:
        mode = "offline" if self.is_offline else "live"
        return f"<{self.__class__.__name__} {mode}>"
