"""REST API for the JobHunt website (FastAPI).

The website is a thin layer: every endpoint reuses the same engine as the
CLI (JobAggregator, ApplicationTracker, Pydantic models), so all the course
concepts still do the real work. FastAPI adds automatic request validation
(Pydantic again) and interactive docs at /docs.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, ValidationError

from . import __version__
from .aggregator import JobAggregator
from .config import PROJECT_ROOT, Settings
from .models import ALLOWED_TRANSITIONS, Application, ApplicationStatus, Job, JobType, SearchQuery
from .sources import ALL_SOURCES
from .storage import JsonStore
from .tracker import ApplicationTracker, TrackerError

WEB_DIST = PROJECT_ROOT / "web" / "dist"

BOARD_WEBSITES = {
    "arbeitnow": "https://www.arbeitnow.com",
    "remotive": "https://remotive.com",
    "himalayas": "https://himalayas.app",
}


# ---- response models (what the React app receives) ---------------------------


class SourceInfo(BaseModel):
    name: str
    website: str
    api_url: str


class SearchResponse(BaseModel):
    query: SearchQuery
    jobs: list[Job]
    per_source: dict[str, int]
    errors: dict[str, str]
    matched: int
    offline: bool


class ApplicationOut(BaseModel):
    id: str
    status: ApplicationStatus
    job: Job
    history: list[dict]

    @classmethod
    def from_app(cls, app: Application) -> "ApplicationOut":
        return cls(
            id=app.job.fingerprint,
            status=app.status,
            job=app.job,
            history=[change.model_dump(mode="json") for change in app.history],
        )


class StatusUpdate(BaseModel):
    status: ApplicationStatus
    note: str | None = Field(default=None, max_length=300)


# ---- app factory --------------------------------------------------------------


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    store = JsonStore(settings.data_dir)

    app = FastAPI(
        title="JobHunt API",
        version=__version__,
        description="Search several job boards at once and track applications.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def tracker() -> ApplicationTracker:
        # A fresh tracker per request always reads the latest JSON file.
        return ApplicationTracker(store)

    # ---- errors -> clean JSON messages for the frontend ----
    @app.exception_handler(TrackerError)
    async def _tracker_error(_: Request, exc: TrackerError) -> JSONResponse:
        code = 404 if "no tracked job" in str(exc) else 409
        return JSONResponse(status_code=code, content={"detail": str(exc)})

    @app.exception_handler(ValidationError)
    async def _validation_error(_: Request, exc: ValidationError) -> JSONResponse:
        messages = [
            f"{'.'.join(str(p) for p in err['loc']) or 'input'}: {err['msg']}"
            for err in exc.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": "; ".join(messages)})

    # ---- endpoints ----
    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/api/sources", response_model=list[SourceInfo])
    async def sources() -> list[SourceInfo]:
        return [
            SourceInfo(name=name, website=BOARD_WEBSITES.get(name, cls.base_url), api_url=cls.base_url)
            for name, cls in ALL_SOURCES.items()
        ]

    @app.get("/api/search", response_model=SearchResponse)
    async def search(
        keyword: str = Query(..., description='e.g. "python", "react", "intern"'),
        location: str | None = None,
        remote: bool = False,
        job_type: JobType | None = None,
        days: int | None = None,
        limit: int = 30,
        sources: str | None = Query(None, description="comma list, e.g. remotive,himalayas"),
        offline: bool = False,
    ) -> SearchResponse:
        query = SearchQuery(
            keyword=keyword,
            location=location or None,
            remote_only=remote,
            job_type=job_type,
            max_age_days=days,
            limit=limit,
        )
        run_settings = settings.model_copy(update={"offline": offline or settings.offline})
        names = [s for s in (sources or "").split(",") if s] or None
        try:
            aggregator = JobAggregator(run_settings, names)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        result = await aggregator.search(query)
        if result.jobs:
            store.save_results(result.jobs)
        return SearchResponse(
            query=query,
            jobs=result.jobs,
            per_source=result.per_source,
            errors=result.errors,
            matched=result.raw_total,
            offline=run_settings.offline,
        )

    @app.get("/api/jobs/{job_id}", response_model=Job)
    async def job_detail(job_id: str) -> Job:
        """A job from the latest search, or from the tracker (so links survive a refresh)."""
        for job in store.load_results():
            if job.fingerprint == job_id:
                return job
        for application in tracker().iter_by_status():
            if application.job.fingerprint == job_id:
                return application.job
        raise HTTPException(status_code=404, detail="Job not found. Run a new search.")

    @app.get("/api/applications", response_model=list[ApplicationOut])
    async def list_applications(status: ApplicationStatus | None = None) -> list[ApplicationOut]:
        apps = sorted(
            tracker().iter_by_status(status),
            key=lambda a: a.history[-1].at,
            reverse=True,
        )
        return [ApplicationOut.from_app(a) for a in apps]

    @app.post("/api/applications", response_model=ApplicationOut, status_code=201)
    async def save_application(job: Job) -> ApplicationOut:
        return ApplicationOut.from_app(tracker().add(job))

    @app.patch("/api/applications/{app_id}", response_model=ApplicationOut)
    async def update_application(app_id: str, change: StatusUpdate) -> ApplicationOut:
        updated = tracker().update_status(app_id, change.status, change.note)
        return ApplicationOut.from_app(updated)

    @app.delete("/api/applications/{app_id}", status_code=204)
    async def delete_application(app_id: str) -> None:
        tracker().remove(app_id)

    @app.get("/api/report")
    async def report() -> dict[str, object]:
        return tracker().report()

    @app.get("/api/transitions")
    async def transitions() -> dict[str, list[str]]:
        """Which status moves are allowed, so the UI only offers valid buttons."""
        return {k.value: sorted(s.value for s in v) for k, v in ALLOWED_TRANSITIONS.items()}

    # ---- the built React app (after `npm run build`) ----
    if WEB_DIST.exists():

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa(full_path: str) -> FileResponse:
            if full_path.startswith("api/"):
                raise HTTPException(status_code=404, detail="Not found")
            candidate = (WEB_DIST / full_path).resolve()
            if full_path and candidate.is_file() and WEB_DIST.resolve() in candidate.parents:
                return FileResponse(candidate)
            return FileResponse(WEB_DIST / "index.html")  # React Router handles the URL

    return app


def run(host: str = "127.0.0.1", port: int = 8000, offline: bool = False) -> None:
    import uvicorn

    settings = Settings.from_env(offline=offline or None)
    uvicorn.run(create_app(settings), host=host, port=port, log_level="info")

