import asyncio
import json

import aiohttp
import pytest

from jobhunt.aggregator import JobAggregator
from jobhunt.config import PROJECT_ROOT, Settings
from jobhunt.models import JobType, SearchQuery
from jobhunt.pipeline import batched, deduplicate, take
from jobhunt.sources import ArbeitnowSource, JobSource, SourceError


@pytest.fixture
def settings(tmp_path):
    return Settings(data_dir=tmp_path, offline=True)


def search(settings, **query):
    return asyncio.run(JobAggregator(settings).search(SearchQuery(**query)))


def test_offline_search_merges_all_sources(settings):
    result = search(settings, keyword="python", limit=50)
    assert set(result.per_source) == {"arbeitnow", "remotive", "himalayas"}
    assert not result.errors
    assert len(result.jobs) > 5


def test_invalid_items_are_skipped_not_fatal():
    source = ArbeitnowSource(fixture_dir=PROJECT_ROOT / "data" / "samples")
    payload = json.loads((PROJECT_ROOT / "data/samples/arbeitnow.json").read_text())
    jobs = list(source.parse(payload))
    assert source.stats["skipped"] == 1
    assert len(jobs) == source.stats["valid"] == len(payload["data"]) - 1


def test_cross_board_duplicates_removed(settings):
    result = search(settings, keyword="python", limit=50)
    fingerprints = [job.fingerprint for job in result.jobs]
    assert len(fingerprints) == len(set(fingerprints))
    assert result.duplicates_removed >= 2


def test_filters(settings):
    remote = search(settings, keyword="python", remote_only=True, limit=50)
    assert remote.jobs and all(job.remote for job in remote.jobs)
    interns = search(settings, keyword="python", job_type=JobType.INTERNSHIP, limit=50)
    assert interns.jobs and all(job.job_type is JobType.INTERNSHIP for job in interns.jobs)
    capped = search(settings, keyword="python", limit=3)
    assert len(capped.jobs) == 3


def test_results_sorted_newest_first(settings):
    jobs = search(settings, keyword="python", limit=50).jobs
    dates = [job.posted_at for job in jobs if job.posted_at]
    assert dates == sorted(dates, reverse=True)


def test_unknown_source_rejected(settings):
    with pytest.raises(ValueError):
        JobAggregator(settings, ["linkedin"])


def test_one_failing_source_does_not_break_search(settings, monkeypatch):
    async def boom(self, query):
        raise SourceError("remotive: down for maintenance")

    monkeypatch.setattr("jobhunt.sources.RemotiveSource.fetch", boom)
    result = search(settings, keyword="python")
    assert "remotive" in result.errors
    assert result.jobs  # the other two boards still answered


def test_sources_run_concurrently(settings, monkeypatch):
    original = JobSource.fetch

    async def slow_fetch(self, query):
        await asyncio.sleep(0.3)
        return await original(self, query)

    monkeypatch.setattr(JobSource, "fetch", slow_fetch)
    loop_start = asyncio.run(_timed(JobAggregator(settings), SearchQuery(keyword="python")))
    assert loop_start < 0.8  # 3 x 0.3s sequentially would be ~0.9s+


async def _timed(aggregator, query):
    start = asyncio.get_running_loop().time()
    await aggregator.search(query)
    return asyncio.get_running_loop().time() - start


def test_retry_then_source_error_on_network_failure():
    calls = {"n": 0}

    class FlakySession:
        def get(self, *args, **kwargs):
            calls["n"] += 1
            raise aiohttp.ClientConnectionError("no route to host")

    source = ArbeitnowSource(session=FlakySession())  # type: ignore[arg-type]
    with pytest.raises(SourceError):
        asyncio.run(source.fetch(SearchQuery(keyword="python")))
    assert calls["n"] == 3  # @retry(attempts=3)


def test_generators_are_lazy():
    pulled = []

    def endless():
        n = 0
        while True:
            pulled.append(n)
            yield n
            n += 1

    assert list(take(endless(), 3)) == [0, 1, 2]
    assert len(pulled) == 3  # never ran ahead
    assert list(batched(iter(range(5)), 2)) == [[0, 1], [2, 3], [4]]
    assert list(deduplicate([])) == []
