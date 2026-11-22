"""Jooble live search. No network connection and no API key is printed."""

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from providers.jooble.client import JoobleError, search_jobs
from providers.jooble.normalize import dedupe_jobs, normalize_jobs
from providers.jooble.quota import reset
from routes.jobs import read_jooble_jobs
from services.matching import eligible_for_ranking, score_job

INDIA_KEY = "india-test-key"
UK_KEY = "uk-test-key"
NOW = datetime(2026, 11, 23, tzinfo=timezone.utc)


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def _env(monkeypatch):
    monkeypatch.setenv("JOOBLE_IN_API_KEY", INDIA_KEY)
    monkeypatch.setenv("JOOBLE_UK_API_KEY", UK_KEY)
    reset()


def _row(**overrides):
    row = {
        "id": 501,
        "title": "Software Engineer",
        "location": "Bengaluru",
        "snippet": "<b>Build</b> services",
        "salary": "₹900000 - ₹1200000",
        "source": "Example Board",
        "type": "Full-time",
        "link": "https://in.jooble.org/jdp/501?utm_source=newsletter",
        "company": "Harbor",
        "updated": "2026-11-22T08:00:00.0000000",
    }
    row.update(overrides)
    return row


def _post(monkeypatch, responses):
    calls = []

    def post(url, json=None, headers=None, timeout=None):
        calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        result = responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr("providers.jooble.client.requests.post", post)
    return calls


def test_india_and_uk_use_separate_endpoints_and_keys(monkeypatch):
    _env(monkeypatch)
    calls = _post(monkeypatch, [FakeResponse(200, {"jobs": [_row()]}), FakeResponse(200, {"jobs": [_row(id=8, title="Nurse", location="Manchester", link="https://uk.jooble.org/jdp/8", salary="")]})])

    india = search_jobs(country="in", keywords="Software Engineer", location="Bengaluru", now=NOW)
    uk = search_jobs(country="uk", keywords="Nurse", now=NOW)

    assert calls[0]["url"] == f"https://in.jooble.org/api/{INDIA_KEY}"
    assert calls[1]["url"] == f"https://uk.jooble.org/api/{UK_KEY}"
    assert INDIA_KEY not in calls[1]["url"]
    assert UK_KEY not in calls[0]["url"]
    assert calls[0]["headers"]["Content-Type"] == "application/json"
    assert calls[0]["json"] == {
        "keywords": "Software Engineer",
        "location": "Bengaluru",
        "page": "1",
        "companysearch": False,
        "ResultOnPage": "10",
    }
    assert calls[1]["json"]["location"] == "United Kingdom"
    assert calls[0]["timeout"] == (5, 15)
    assert india[0].source_country == "in"
    assert uk[0].source_country == "gb"
    assert len(calls) == 2


def test_a_repeated_search_does_not_call_jooble_again(monkeypatch):
    _env(monkeypatch)
    calls = _post(monkeypatch, [FakeResponse(200, {"jobs": [_row()]})])
    search_jobs(country="in", keywords="Software Engineer", location="Bengaluru", now=NOW)
    search_jobs(country="in", keywords=" software   engineer ", location="Bengaluru", now=NOW)
    assert len(calls) == 1


def test_normalization_keeps_only_supplied_facts():
    job = normalize_jobs([_row()], "in")[0].as_dict()
    assert job["source"] == "jooble"
    assert job["publisher"] == "Example Board"
    assert job["company"] == "Harbor"
    assert job["location"] == "Bengaluru"
    assert job["description"] == "Build services"
    assert job["source_url"].startswith("https://in.jooble.org/jdp/501")
    assert job["external_job_id"] == "501"
    assert job["salary_currency"] == "INR"
    assert job["salary_min"] == 900000
    assert job["salary_max"] == 1200000
    assert job["contract_time"] == "full_time"
    assert job["category_label"] is None
    assert job["category_tag"] is None
    assert job["required_skills"] == []
    assert job["is_matchable"] is False
    assert job["requirements_available"] is False

    blank = normalize_jobs(
        [_row(company="", location="", salary="40000", type="freelance", link="notaurl", snippet="")],
        "in",
    )[0].as_dict()
    assert blank["company"] == ""
    assert blank["location"] == ""
    assert blank["salary_currency"] is None
    assert blank["salary_min"] is None
    assert blank["source_url"] is None
    assert blank["contract_time"] is None
    assert normalize_jobs([{"company": "Harbor"}], "in") == []


def test_duplicates_use_url_id_or_the_full_triple():
    first = normalize_jobs([_row()], "in")[0]
    same_url = normalize_jobs([_row(id=999, link="https://in.jooble.org/jdp/501")], "in")[0]
    same_title = normalize_jobs(
        [_row(id=77, title="Software Engineer", company="Other", location="Delhi", link="https://example.com/other")],
        "in",
    )[0]
    catalogue = [{"title": "Nurse", "company": "Harbor", "location": "York", "source": "adzuna", "source_url": "https://example.com/kept"}]
    kept = dedupe_jobs([first, same_url, same_title], catalogue)
    assert [job.title for job in kept] == ["Software Engineer", "Software Engineer"]
    assert kept[1].company == "Other"


def test_provider_failures_are_safe(monkeypatch, caplog):
    _env(monkeypatch)
    caplog.set_level(logging.WARNING)
    cases = [
        (FakeResponse(403, {"error": INDIA_KEY}), "rejected the API key"),
        (FakeResponse(404, {}), "endpoint"),
        (FakeResponse(429, {"message": INDIA_KEY}), "request limit"),
        (requests.Timeout("timed out " + INDIA_KEY), "did not respond"),
        (requests.ConnectionError("dns " + UK_KEY), "could not be reached"),
        (FakeResponse(200, ValueError("not json " + INDIA_KEY)), "could not be read"),
    ]
    for result, phrase in cases:
        reset()
        _post(monkeypatch, [result])
        with pytest.raises(JoobleError) as caught:
            search_jobs(country="in", keywords="Engineer", location="Pune", now=NOW)
        assert phrase in str(caught.value)
        assert INDIA_KEY not in str(caught.value)
        assert UK_KEY not in str(caught.value)
    assert INDIA_KEY not in caplog.text
    assert UK_KEY not in caplog.text


def test_the_daily_safety_limit_stops_further_requests(monkeypatch):
    _env(monkeypatch)
    calls = _post(monkeypatch, [FakeResponse(200, {"jobs": []}) for _ in range(3)])
    search_jobs(country="in", keywords="One", now=NOW, limit=2)
    search_jobs(country="in", keywords="Two", now=NOW, limit=2)
    with pytest.raises(JoobleError, match="limit"):
        search_jobs(country="in", keywords="Three", now=NOW, limit=2)
    assert len(calls) == 2
    search_jobs(country="gb", keywords="One", now=NOW, limit=2)
    assert len(calls) == 3


def test_route_returns_live_jobs_without_a_database(monkeypatch):
    _env(monkeypatch)
    _post(monkeypatch, [FakeResponse(200, {"jobs": [_row()]})])
    body = read_jooble_jobs("in", "Software Engineer", "Bengaluru")
    assert body["detail"] is None
    assert body["jobs"][0]["source"] == "jooble"
    assert INDIA_KEY not in str(body)
    with pytest.raises(Exception) as caught:
        read_jooble_jobs("us", "Engineer", None)
    assert getattr(caught.value, "status_code", None) == 422


def test_jooble_listings_do_not_change_the_match_formula():
    candidate = SimpleNamespace(skills=["Python"], preferred_roles=["Developer"], preferred_locations=["London"])
    plain = SimpleNamespace(
        title="Python Developer",
        location="London",
        required_skills=["Python"],
        is_matchable=True,
        requirements_available=True,
    )
    labelled = SimpleNamespace(
        title="Python Developer",
        location="London",
        required_skills=["Python"],
        is_matchable=True,
        requirements_available=True,
        category_label="IT Jobs",
    )
    scored = score_job(candidate, plain)
    assert score_job(candidate, labelled).total_score == scored.total_score
    assert (scored.skill_score, scored.role_score, scored.location_score) == (70, 20, 10)
    live = SimpleNamespace(**normalize_jobs([_row(title="Python Developer")], "in")[0].as_dict())
    assert eligible_for_ranking(live) is False
