"""Application tracker: save jobs and move them through a hiring pipeline.

Encapsulation: the applications dict is private. The only way to change a
status is `update_status`, which enforces the allowed transitions
(e.g. you cannot go from "rejected" back to "interview").
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator

from .models import (
    ALLOWED_TRANSITIONS,
    Application,
    ApplicationStatus,
    Job,
    StatusChange,
)
from .storage import JsonStore


class TrackerError(Exception):
    pass


class ApplicationTracker:
    def __init__(self, store: JsonStore) -> None:
        self._store = store
        self._apps: dict[str, Application] = store.load_applications()

    def __len__(self) -> int:
        return len(self._apps)

    def __contains__(self, job_id: str) -> bool:
        return job_id in self._apps

    def add(self, job: Job) -> Application:
        if job.fingerprint in self._apps:
            raise TrackerError(f"'{job.title}' at {job.company} is already tracked")
        app = Application(job=job)
        self._apps[job.fingerprint] = app
        self._store.save_applications(self._apps)
        return app

    def get(self, job_id: str) -> Application:
        matches = [key for key in self._apps if key.startswith(job_id)]
        if not matches:
            raise TrackerError(f"no tracked job with id '{job_id}'")
        if len(matches) > 1:
            raise TrackerError(f"id '{job_id}' is ambiguous, type more characters")
        return self._apps[matches[0]]

    def update_status(
        self, job_id: str, new_status: ApplicationStatus, note: str | None = None
    ) -> Application:
        app = self.get(job_id)
        if new_status not in ALLOWED_TRANSITIONS[app.status]:
            allowed = ", ".join(s.value for s in ALLOWED_TRANSITIONS[app.status]) or "none"
            raise TrackerError(
                f"cannot move from '{app.status.value}' to '{new_status.value}' "
                f"(allowed: {allowed})"
            )
        app.status = new_status
        app.history.append(StatusChange(status=new_status, note=note))
        self._store.save_applications(self._apps)
        return app

    def remove(self, job_id: str) -> Application:
        app = self.get(job_id)
        del self._apps[app.job.fingerprint]
        self._store.save_applications(self._apps)
        return app

    def iter_by_status(self, status: ApplicationStatus | None = None) -> Iterator[Application]:
        """Generator over tracked applications, optionally filtered."""
        for app in self._apps.values():
            if status is None or app.status == status:
                yield app

    def report(self) -> dict[str, object]:
        counts = Counter(app.status.value for app in self._apps.values())
        applied = sum(counts[s] for s in ("applied", "interview", "offer", "rejected", "selected"))
        interviews = sum(counts[s] for s in ("interview", "offer", "selected"))
        sources = Counter(app.job.source for app in self._apps.values())
        return {
            "total_tracked": len(self._apps),
            "by_status": {s.value: counts.get(s.value, 0) for s in ApplicationStatus},
            "by_source": dict(sources),
            "interview_rate": round(interviews / applied * 100, 1) if applied else 0.0,
        }
