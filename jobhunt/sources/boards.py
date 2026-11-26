"""Concrete job boards. Each one only knows its own API format.

All three are free and need no API key:
- Arbeitnow  https://www.arbeitnow.com/api/job-board-api   (Europe + remote)
- Remotive   https://remotive.com/api/remote-jobs          (remote, server-side search)
- Himalayas  https://himalayas.app/jobs/api/search         (remote, server-side search)
"""

from __future__ import annotations

from typing import Any

from ..models import Job, JobType, SearchQuery
from .base import JobSource


class ArbeitnowSource(JobSource):
    name = "arbeitnow"
    base_url = "https://www.arbeitnow.com/api/job-board-api"

    def build_params(self, query: SearchQuery) -> dict[str, Any]:
        # No server-side search: we fetch the latest page and filter locally.
        return {"page": 1}

    def extract_items(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        return payload.get("data", [])

    def to_job(self, raw: dict[str, Any]) -> Job:
        return Job(
            source=self.name,
            source_id=raw["slug"],
            title=raw["title"],
            company=raw["company_name"],
            location=raw.get("location") or "Not specified",
            remote=bool(raw.get("remote")),
            job_type=JobType.best_of(raw.get("job_types")),
            tags=raw.get("tags"),
            url=raw["url"],
            posted_at=raw.get("created_at"),
            description=raw.get("description", ""),
        )


class RemotiveSource(JobSource):
    name = "remotive"
    base_url = "https://remotive.com/api/remote-jobs"

    def build_params(self, query: SearchQuery) -> dict[str, Any]:
        return {"search": query.keyword, "limit": max(query.limit * 3, 50)}

    def extract_items(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        return payload.get("jobs", [])

    def to_job(self, raw: dict[str, Any]) -> Job:
        return Job(
            source=self.name,
            source_id=str(raw["id"]),
            title=raw["title"],
            company=raw["company_name"],
            location=raw.get("candidate_required_location") or "Remote",
            remote=True,  # Remotive only lists remote roles
            job_type=JobType.from_raw(raw.get("job_type")),
            tags=raw.get("tags") or [raw.get("category", "")],
            url=raw["url"],
            posted_at=raw.get("publication_date"),
            salary=raw.get("salary"),
            description=raw.get("description", ""),
        )


class HimalayasSource(JobSource):
    name = "himalayas"
    base_url = "https://himalayas.app/jobs/api/search"

    def build_params(self, query: SearchQuery) -> dict[str, Any]:
        return {"q": query.keyword, "sort": "recent", "page": 1}

    def extract_items(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        return payload.get("jobs", [])

    def to_job(self, raw: dict[str, Any]) -> Job:
        restrictions = raw.get("locationRestrictions") or []
        low, high = raw.get("minSalary"), raw.get("maxSalary")
        salary = f"{raw.get('currency', 'USD')} {low:,}–{high:,}" if low and high else None
        return Job(
            source=self.name,
            source_id=raw.get("guid") or raw["applicationLink"],
            title=raw["title"],
            company=raw["companyName"],
            location=", ".join(restrictions[:3]) if restrictions else "Worldwide (remote)",
            remote=True,
            job_type=JobType.from_raw(raw.get("employmentType")),
            tags=(raw.get("categories") or [])[:5] + (raw.get("seniority") or []),
            url=raw["applicationLink"],
            posted_at=raw.get("pubDate"),
            salary=salary,
            description=raw.get("description") or raw.get("excerpt", ""),
        )


# Registry: add a new board by writing one subclass and listing it here.
ALL_SOURCES: dict[str, type[JobSource]] = {
    cls.name: cls for cls in (ArbeitnowSource, RemotiveSource, HimalayasSource)
}
