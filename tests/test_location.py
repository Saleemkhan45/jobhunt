import pytest

from jobhunt.models import Job
from jobhunt.pipeline import location_matches


def job(location, remote=True):
    return Job(source="t", source_id=location, title="Graphic Designer", company="Acme",
               url="https://example.com/x", location=location, remote=remote)


@pytest.mark.parametrize(
    ("location", "remote", "expected"),
    [
        ("Philippines", True, False),
        ("Worldwide", True, True),
        ("Worldwide (remote)", True, True),
        ("Remote", True, True),
        ("Asia, Europe", True, True),
        ("Pakistan, India, Bangladesh", True, True),
        ("Lahore, Pakistan", False, True),
        ("Berlin", False, False),
        ("United States, Canada", True, False),
    ],
)
def test_location_for_pakistan(location, remote, expected):
    assert location_matches(job(location, remote), "Pakistan") is expected


def test_city_and_region_matching():
    assert location_matches(job("Berlin", remote=False), "berlin")
    assert location_matches(job("Europe", remote=True), "Germany")
    assert not location_matches(job("Europe", remote=True), "Pakistan")


@pytest.mark.parametrize(
    ("location", "remote", "wanted", "expected"),
    [
        # Short names must not match inside longer words.
        ("Australia", True, "USA", False),
        ("Russia", True, "USA", False),
        ("Indiana", False, "India", False),
        ("Ukraine", True, "UK", False),
        # Whole words and multi-word regions still match.
        ("United States", True, "USA", True),
        ("US, Canada", True, "USA", True),
        ("Bangalore, India", False, "India", True),
        ("Europe", True, "UK", True),
    ],
)
def test_whole_word_matching(location, remote, wanted, expected):
    assert location_matches(job(location, remote), wanted) is expected
