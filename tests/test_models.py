import pytest
from pydantic import ValidationError

from jobhunt.models import Job, JobType, SearchQuery


def make_job(**overrides):
    data = {
        "source": "test",
        "source_id": "1",
        "title": "<b>Python Developer</b> (m/f/d)",
        "company": "Acme &amp; Co",
        "url": "https://example.com/job/1",
        "posted_at": 1764000000,
        "tags": ["Python", "python", " Backend "],
        "description": "<p>Hello <i>world</i></p>",
    }
    data.update(overrides)
    return Job(**data)


def test_html_is_cleaned_and_tags_deduplicated():
    job = make_job()
    assert job.title == "Python Developer (m/f/d)"
    assert job.company == "Acme & Co"
    assert job.description == "Hello world"
    assert job.tags == ["python", "backend"]


def test_unix_and_iso_dates_both_parse():
    assert make_job(posted_at=1764000000).posted_at.year == 2025
    assert make_job(posted_at="2026-11-20T10:00:00").posted_at.tzinfo is not None


def test_invalid_url_is_rejected():
    with pytest.raises(ValidationError):
        make_job(url="not-a-url")


def test_remote_inferred_from_location():
    assert make_job(location="Remote - EU").remote is True


def test_fingerprint_ignores_case_and_gender_suffix():
    a = make_job(title="Python Developer (m/f/d)", company="Shopwise")
    b = make_job(title="python developer", company="SHOPWISE", source="other")
    assert a.fingerprint == b.fingerprint


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Full Time", JobType.FULL_TIME),
        ("full_time", JobType.FULL_TIME),
        ("Working Student", JobType.INTERNSHIP),
        ("Contractor", JobType.CONTRACT),
        (None, JobType.OTHER),
    ],
)
def test_job_type_mapping(raw, expected):
    assert JobType.from_raw(raw) is expected


def test_search_query_validation():
    assert SearchQuery(keyword="  react  ").keyword == "react"
    with pytest.raises(ValidationError):
        SearchQuery(keyword="x")  # too short
    with pytest.raises(ValidationError):
        SearchQuery(keyword="python; rm -rf")  # symbols
    with pytest.raises(ValidationError):
        SearchQuery(keyword="python", limit=0)


def test_best_job_type_from_several_labels():
    assert JobType.best_of(["berufserfahren", "Full Time"]) is JobType.FULL_TIME
    assert JobType.best_of(["Praktikum"]) is JobType.INTERNSHIP
    assert JobType.best_of([]) is JobType.OTHER


def test_long_description_kept_for_search():
    job = make_job(description="intro " * 200 + "we use Python")
    assert job.matches("python")
