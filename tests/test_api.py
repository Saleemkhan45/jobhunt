import pytest
from fastapi.testclient import TestClient

from jobhunt.api import create_app
from jobhunt.config import Settings
from jobhunt.models import clean_multiline


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(Settings(data_dir=tmp_path, offline=True)))


def test_health_and_sources(client):
    assert client.get("/api/health").json()["status"] == "ok"
    names = {s["name"] for s in client.get("/api/sources").json()}
    assert names == {"arbeitnow", "remotive", "himalayas"}


def test_search_returns_validated_jobs(client):
    data = client.get("/api/search", params={"keyword": "python", "limit": 5}).json()
    assert data["offline"] is True
    assert len(data["jobs"]) == 5
    assert set(data["per_source"]) == {"arbeitnow", "remotive", "himalayas"}
    first = data["jobs"][0]
    assert first["fingerprint"] and first["url"].startswith("https://")


def test_search_filters_and_bad_input(client):
    remote = client.get("/api/search", params={"keyword": "python", "remote": True}).json()
    assert all(job["remote"] for job in remote["jobs"])
    bad = client.get("/api/search", params={"keyword": "x"})
    assert bad.status_code == 422
    assert "keyword" in bad.json()["detail"]
    unknown = client.get("/api/search", params={"keyword": "python", "sources": "linkedin"})
    assert unknown.status_code == 400


def test_job_detail_after_search(client):
    job = client.get("/api/search", params={"keyword": "python"}).json()["jobs"][0]
    detail = client.get(f"/api/jobs/{job['fingerprint']}")
    assert detail.status_code == 200
    assert detail.json()["title"] == job["title"]
    assert client.get("/api/jobs/doesnotexist").status_code == 404


def test_tracker_flow_over_http(client):
    job = client.get("/api/search", params={"keyword": "python"}).json()["jobs"][0]

    created = client.post("/api/applications", json=job)
    assert created.status_code == 201
    app_id = created.json()["id"]
    assert client.post("/api/applications", json=job).status_code == 409  # duplicate

    assert client.patch(f"/api/applications/{app_id}", json={"status": "applied"}).status_code == 200
    moved = client.patch(f"/api/applications/{app_id}", json={"status": "interview", "note": "Fri"})
    assert moved.json()["status"] == "interview"
    assert len(moved.json()["history"]) == 3

    backwards = client.patch(f"/api/applications/{app_id}", json={"status": "applied"})
    assert backwards.status_code == 409

    report = client.get("/api/report").json()
    assert report["total_tracked"] == 1 and report["interview_rate"] == 100.0
    assert client.get("/api/transitions").json()["rejected"] == []

    assert client.delete(f"/api/applications/{app_id}").status_code == 204
    assert client.get("/api/applications").json() == []


def test_description_keeps_paragraphs_as_plain_text():
    text = clean_multiline("<p>About us</p><ul><li>Python</li><li>SQL &amp; APIs</li></ul><p>Apply!</p>")
    assert text == "About us\n\n• Python\n• SQL & APIs\n\nApply!"
    assert "<" not in text
