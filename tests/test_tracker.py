import pytest

from jobhunt.cli import main
from jobhunt.models import ApplicationStatus as S
from jobhunt.models import Job
from jobhunt.storage import JsonStore
from jobhunt.tracker import ApplicationTracker, TrackerError


def job(title="Python Intern", company="Acme"):
    return Job(source="test", source_id=title, title=title, company=company,
               url="https://example.com/x")


@pytest.fixture
def store(tmp_path):
    return JsonStore(tmp_path)


def test_full_hiring_flow_persists(store):
    tracker = ApplicationTracker(store)
    app = tracker.add(job())
    key = app.job.fingerprint[:6]
    tracker.update_status(key, S.APPLIED)
    tracker.update_status(key, S.INTERVIEW, note="Tech round Friday")

    reloaded = ApplicationTracker(store)  # fresh object reads the JSON file
    app = reloaded.get(key)
    assert app.status is S.INTERVIEW
    assert [h.status for h in app.history] == [S.SAVED, S.APPLIED, S.INTERVIEW]
    assert app.history[-1].note == "Tech round Friday"


def test_invalid_transition_rejected(store):
    tracker = ApplicationTracker(store)
    key = tracker.add(job()).job.fingerprint
    tracker.update_status(key, S.REJECTED)
    with pytest.raises(TrackerError, match="cannot move"):
        tracker.update_status(key, S.INTERVIEW)


def test_duplicate_and_missing(store):
    tracker = ApplicationTracker(store)
    tracker.add(job())
    with pytest.raises(TrackerError, match="already tracked"):
        tracker.add(job())
    with pytest.raises(TrackerError, match="no tracked job"):
        tracker.get("zzzzzz")


def test_report(store):
    tracker = ApplicationTracker(store)
    a = tracker.add(job("Job A")).job.fingerprint
    b = tracker.add(job("Job B")).job.fingerprint
    tracker.add(job("Job C"))
    tracker.update_status(a, S.APPLIED)
    tracker.update_status(b, S.APPLIED)
    tracker.update_status(b, S.INTERVIEW)
    report = tracker.report()
    assert report["total_tracked"] == 3
    assert report["by_status"]["saved"] == 1
    assert report["interview_rate"] == 50.0


def test_cli_end_to_end(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("JOBHUNT_DATA_DIR", str(tmp_path))
    assert main(["--offline", "search", "python", "--limit", "5"]) == 0
    assert main(["show", "1"]) == 0
    assert main(["save", "1"]) == 0
    assert main(["list"]) == 0
    assert main(["report", "--export"]) == 0
    assert (tmp_path / "report.json").exists()
    assert main(["save", "99"]) == 1  # out of range -> friendly error
    assert main(["--offline", "search", "x"]) == 2  # pydantic rejects short keyword
