"""Pydantic models: every piece of data entering the app is validated here.

Raw API responses are messy (HTML in descriptions, unix timestamps vs ISO
strings, missing fields). Each source maps its raw dict into a `Job`, and the
validators below normalise it, so the rest of the app can trust the data.
"""

from __future__ import annotations

import hashlib
import html
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    computed_field,
    field_validator,
    model_validator,
)

_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")


def clean_text(value: str | None) -> str:
    """Strip HTML tags/entities and collapse whitespace."""
    if not value:
        return ""
    text = html.unescape(_TAG_RE.sub(" ", value))
    return _SPACE_RE.sub(" ", text).strip()


class JobType(str, Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    FREELANCE = "freelance"
    OTHER = "other"

    @classmethod
    def from_raw(cls, raw: str | None) -> "JobType":
        """Map the many spellings APIs use ("Full Time", "full-time", ...)."""
        if not raw:
            return cls.OTHER
        key = raw.lower().replace("-", " ").replace("_", " ")
        # English and German spellings (Arbeitnow is a German job board)
        if any(w in key for w in ("intern", "working student", "trainee", "praktikum", "werkstudent")):
            return cls.INTERNSHIP
        if any(w in key for w in ("part", "teilzeit", "minijob")):
            return cls.PART_TIME
        if any(w in key for w in ("contract", "temporary", "befristet")):
            return cls.CONTRACT
        if any(w in key for w in ("freelance", "freiberuf")):
            return cls.FREELANCE
        if any(w in key for w in ("full", "permanent", "vollzeit", "festanstellung")):
            return cls.FULL_TIME
        return cls.OTHER

    @classmethod
    def best_of(cls, values: list[str] | None) -> "JobType":
        """Several labels (e.g. ["berufserfahren", "Full Time"]) -> first one we recognise."""
        for value in values or []:
            job_type = cls.from_raw(value)
            if job_type is not cls.OTHER:
                return job_type
        return cls.OTHER


class Job(BaseModel):
    """One normalised job posting, whichever API it came from."""

    model_config = ConfigDict(str_strip_whitespace=True)

    source: str
    source_id: str
    title: str = Field(min_length=2, max_length=300)
    company: str = Field(min_length=1, max_length=200)
    location: str = "Not specified"
    remote: bool = False
    job_type: JobType = JobType.OTHER
    tags: list[str] = Field(default_factory=list)
    url: HttpUrl
    posted_at: datetime | None = None
    salary: str | None = None
    description: str = ""

    @field_validator("title", "company", "location", mode="before")
    @classmethod
    def _strip_html(cls, value: Any) -> Any:
        return clean_text(value) if isinstance(value, str) else value

    @field_validator("description", mode="before")
    @classmethod
    def _clean_description(cls, value: Any) -> str:
        # Keep the full text so keyword search can look through all of it;
        # the CLI shortens it only when displaying.
        text = clean_text(value if isinstance(value, str) else "")
        return text[:8000]

    @field_validator("tags", mode="before")
    @classmethod
    def _normalise_tags(cls, value: Any) -> list[str]:
        if not value:
            return []
        if isinstance(value, str):
            value = value.split(",")
        seen: list[str] = []
        for tag in value:
            tag = clean_text(str(tag)).lower()
            if tag and tag not in seen:
                seen.append(tag)
        return seen[:15]

    @field_validator("salary", mode="before")
    @classmethod
    def _empty_salary(cls, value: Any) -> str | None:
        return (str(value).strip() or None) if value not in (None, "") else None

    @field_validator("posted_at", mode="before")
    @classmethod
    def _parse_date(cls, value: Any) -> datetime | None:
        """APIs send unix seconds (Arbeitnow, Himalayas) or ISO text (Remotive)."""
        if value in (None, "", 0):
            return None
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)
        if isinstance(value, str):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        return value

    @model_validator(mode="after")
    def _infer_remote(self) -> "Job":
        if not self.remote and "remote" in f"{self.location} {self.title}".lower():
            self.remote = True
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def fingerprint(self) -> str:
        """Same role posted on two boards -> same fingerprint (used for de-dup)."""
        norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())  # noqa: E731
        title = re.sub(r"\(.*?\)", "", self.title)  # drop "(m/f/d)" etc.
        return hashlib.sha1(f"{norm(title)}|{norm(self.company)}".encode()).hexdigest()[:12]

    def matches(self, keyword: str) -> bool:
        haystack = f"{self.title} {self.company} {' '.join(self.tags)} {self.description}"
        return keyword.lower() in haystack.lower()


class SearchQuery(BaseModel):
    """Validated user input from the CLI."""

    keyword: str = Field(min_length=2, max_length=60)
    location: str | None = Field(default=None, max_length=60)
    remote_only: bool = False
    job_type: JobType | None = None
    limit: int = Field(default=20, ge=1, le=200)
    max_age_days: int | None = Field(default=None, ge=1, le=365)

    @field_validator("keyword")
    @classmethod
    def _no_symbols(cls, value: str) -> str:
        value = value.strip()
        if not re.fullmatch(r"[\w\s\-+.#/]+", value):
            raise ValueError("keyword may contain letters, numbers, spaces and - + . # / only")
        return value


class ApplicationStatus(str, Enum):
    SAVED = "saved"
    APPLIED = "applied"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    SELECTED = "selected"


# Which status changes make sense. Anything else is rejected by the tracker.
ALLOWED_TRANSITIONS: dict[ApplicationStatus, set[ApplicationStatus]] = {
    ApplicationStatus.SAVED: {ApplicationStatus.APPLIED, ApplicationStatus.REJECTED},
    ApplicationStatus.APPLIED: {ApplicationStatus.INTERVIEW, ApplicationStatus.REJECTED},
    ApplicationStatus.INTERVIEW: {
        ApplicationStatus.OFFER,
        ApplicationStatus.REJECTED,
        ApplicationStatus.SELECTED,
    },
    ApplicationStatus.OFFER: {ApplicationStatus.SELECTED, ApplicationStatus.REJECTED},
    ApplicationStatus.REJECTED: set(),
    ApplicationStatus.SELECTED: set(),
}


class StatusChange(BaseModel):
    status: ApplicationStatus
    at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    note: str | None = Field(default=None, max_length=300)


class Application(BaseModel):
    """A job the student is tracking, with its full status history."""

    job: Job
    status: ApplicationStatus = ApplicationStatus.SAVED
    history: list[StatusChange] = Field(default_factory=list)

    @model_validator(mode="after")
    def _seed_history(self) -> "Application":
        if not self.history:
            self.history.append(StatusChange(status=self.status))
        return self
