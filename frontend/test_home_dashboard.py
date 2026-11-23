"""Dashboard figures from mocked API payloads. No database writes."""

import json
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

FRONTEND_DIR = Path(__file__).resolve().parent
if str(FRONTEND_DIR) not in sys.path:
    sys.path.insert(0, str(FRONTEND_DIR))

from home_metrics import (
    average_match_score,
    format_score,
    format_share,
    score_bucket,
    score_distribution,
    skill_breakdown,
    skill_shares,
)
from test_home_profile_saved import APP_PATH, _markdown

JOBS = [
    {"id": 1, "title": "Low Role", "company": "Northwind"},
    {"id": 2, "title": "Mid Role", "company": "Contoso"},
    {"id": 3, "title": "High Role", "company": "Fabrikam"},
    {"id": 4, "title": "Top Role", "company": "Adventure"},
    {"id": 5, "title": "Extra Role", "company": "Wide World"},
]

MATCHES = [
    {
        "job": {"id": 1, "title": "Low Role", "company": "Northwind"},
        "total_score": 10,
        "matched_skills": ["Python"],
        "semantic_matches": [{"required_skill": "React", "candidate_skill": "React.js", "similarity": 0.92}],
        "missing_skills": ["Go"],
    },
    {
        "job": {"id": 2, "title": "Mid Role", "company": "Contoso"},
        "total_score": 30,
        "matched_skills": ["SQL"],
        "semantic_matches": [],
        "missing_skills": ["Java", "AWS"],
    },
    {
        "job": {"id": 3, "title": "High Role", "company": "Fabrikam"},
        "total_score": 64,
        "matched_skills": [],
        "semantic_matches": [],
        "missing_skills": ["Rust"],
    },
    {
        "job": {"id": 4, "title": "Top Role", "company": "Adventure"},
        "total_score": 92,
        "matched_skills": [],
        "semantic_matches": [],
        "missing_skills": [],
    },
]

SAVED = [
    {"id": 1, "created_at": "2026-11-21T09:00:00", "job": {"id": 4, "title": "Top Role", "company": "Adventure"}},
    {"id": 2, "created_at": "2026-11-20T10:00:00", "job": {"id": 1, "title": "Low Role", "company": "Northwind"}},
]


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.status_code = status_code
        self.content = b"" if status_code == 204 else json.dumps(payload).encode()
        self._payload = payload

    def json(self):
        return self._payload


def _match(score, title="Role", company="Co", exact=0, semantic=0, missing=0):
    return {
        "job": {"id": int(score), "title": title, "company": company},
        "total_score": score,
        "matched_skills": ["Skill"] * exact,
        "semantic_matches": [{}] * semantic,
        "missing_skills": ["Gap"] * missing,
    }


def test_score_ranges_and_skill_counts_follow_the_payload():
    assert score_bucket(0) == "0–20"
    assert score_bucket(20) == "0–20"
    assert score_bucket(20.1) == "21–40"
    assert score_bucket(40) == "21–40"
    assert score_bucket(41) == "41–60"
    assert score_bucket(60) == "41–60"
    assert score_bucket(61) == "61–80"
    assert score_bucket(80) == "61–80"
    assert score_bucket(81) == "81–100"
    assert score_bucket(100) == "81–100"
    assert score_distribution(MATCHES) == [
        ("0–20", 1),
        ("21–40", 1),
        ("41–60", 0),
        ("61–80", 1),
        ("81–100", 1),
    ]
    assert skill_breakdown(MATCHES) == {
        "Exact matches": 2,
        "Semantic matches": 1,
        "Missing skills": 4,
    }
    shares = skill_shares(skill_breakdown(MATCHES))
    assert [(label, count) for label, count, _share in shares] == [
        ("Exact matches", 2),
        ("Semantic matches", 1),
        ("Missing skills", 4),
    ]
    assert [format_share(share) for _label, _count, share in shares] == ["28.6%", "14.3%", "57.1%"]
    assert [share for _label, _count, share in skill_shares({"Exact matches": 0, "Semantic matches": 0, "Missing skills": 0})] == [
        None,
        None,
        None,
    ]
    assert format_score(average_match_score(MATCHES)) == "49"
    assert average_match_score([]) is None


@contextmanager
def _dashboard(matches=None, jobs=None, saved=None, match_status=200, match_error=""):
    calls = []
    match_payload = matches if matches is not None else MATCHES
    job_payload = jobs if jobs is not None else JOBS
    saved_payload = saved if saved is not None else SAVED

    def fake_request(method, url, **kwargs):
        calls.append((method, url, kwargs.get("json")))
        if method == "GET" and url.endswith("/jobs/"):
            return FakeResponse(job_payload)
        if method == "GET" and url.endswith("/saved-jobs"):
            return FakeResponse(saved_payload)
        if method == "GET" and url.endswith("/matches"):
            if match_status >= 400:
                return FakeResponse({"detail": match_error}, match_status)
            return FakeResponse(match_payload)
        if method == "GET" and url.endswith(":8001/"):
            return FakeResponse({"status": "ok", "message": "API is running."})
        raise AssertionError(f"Unexpected API call {method} {url}")

    def reject_session_request(*args, **kwargs):
        raise AssertionError("Session.request was called; the mock did not intercept it.")

    with (
        patch("requests.request", fake_request),
        patch("requests.sessions.Session.request", reject_session_request),
    ):
        app = AppTest.from_file(str(APP_PATH))
        app.session_state["nav"] = "Home"
        app.session_state["auth_token"] = "test-token"
        app.session_state["candidate_id"] = 4
        app.session_state["candidate_name"] = "Ada Lovelace"
        app.session_state["profile"] = {
            "id": 4,
            "name": "Ada Lovelace",
            "email": "ada@example.com",
            "skills": ["Python"],
        }
        app.run()
        assert not app.exception, app.exception
        yield app, calls


def _kpi(text: str, label: str) -> str:
    marker = f"<p class='section-label kpi-card'>{label}</p><p class='kpi-value'>"
    start = text.index(marker) + len(marker)
    return text[start:text.index("</p>", start)]


def test_dashboard_cards_charts_and_lists_use_the_mocked_api():
    with _dashboard() as (app, calls):
        text = _markdown(app)
        assert _kpi(text, "Total jobs") == "5"
        assert _kpi(text, "Jobs matched") == "4"
        assert _kpi(text, "Saved jobs") == "2"
        assert _kpi(text, "Average match score") == "49"
        assert "<span class='column-label'>0–20</span><span class='column-value'>1</span>" in text
        assert "<span class='column-label'>21–40</span><span class='column-value'>1</span>" in text
        assert "<span class='column-label'>41–60</span><span class='column-value'>0</span>" in text
        assert "<span class='column-label'>61–80</span><span class='column-value'>1</span>" in text
        assert "<span class='column-label'>81–100</span><span class='column-value'>1</span>" in text
        assert "<span class='legend-label'>Exact matches</span><span class='legend-count'>2</span><span class='legend-share'>28.6%</span>" in text
        assert "<span class='legend-label'>Semantic matches</span><span class='legend-count'>1</span><span class='legend-share'>14.3%</span>" in text
        assert "<span class='legend-label'>Missing skills</span><span class='legend-count'>4</span><span class='legend-share'>57.1%</span>" in text
        assert "not a share of jobs" in text
        assert text.index("Top Role") < text.index("High Role") < text.index("Mid Role")
        assert "Low Role" in text
        assert "Score 92" in text
        assert "Saved 2026-11-21 09:00" in text
        assert any(button.label == "Discover Jobs" for button in app.button)
        assert any(button.label == "Match Insights" for button in app.button)
        assert any(button.label == "My Profile" for button in app.button)
        assert any(button.label == "Saved Jobs" for button in app.button)
        assert any(button.label == "Resume Centre" for button in app.button)
        assert "Every opportunity you explore" not in text
        assert _kpi(text, "Profile completion") == "33%"
        assert not any(method == "POST" for method, _, _ in calls)
        assert sum(url.endswith("/matches") for _, url, _ in calls) == 1
        app.run()
        assert sum(url.endswith("/matches") for _, url, _ in calls) == 1
        assert sum(url.endswith("/jobs/") for _, url, _ in calls) == 1
        assert sum(url.endswith("/saved-jobs") for _, url, _ in calls) == 1
        next(button for button in app.button if button.key == "home-open-resume").click().run()
        assert app.session_state["nav"] == "Resume Centre"


def test_empty_dashboard_explains_the_blank_figures():
    with _dashboard(matches=[], jobs=[], saved=[]) as (app, calls):
        text = _markdown(app)
        assert _kpi(text, "Total jobs") == "0"
        assert _kpi(text, "Jobs matched") == "0"
        assert _kpi(text, "Saved jobs") == "0"
        assert _kpi(text, "Average match score") == "—"
        assert _kpi(text, "Profile completion") == "33%"
        assert "No jobs have been scored yet." in text
        assert "You have not saved any jobs yet." in text
        assert "<span class='column-value'>" not in text
        assert "<span class='legend-count'>" not in text
        assert not any(method == "POST" for method, _, _ in calls)


def test_match_error_does_not_draw_zero_charts():
    with _dashboard(match_status=500, match_error="Ranking failed.") as (app, _calls):
        text = _markdown(app)
        assert _kpi(text, "Total jobs") == "5"
        assert _kpi(text, "Jobs matched") == "—"
        assert _kpi(text, "Average match score") == "—"
        assert _kpi(text, "Saved jobs") == "2"
        assert any("Ranking failed." in item.value for item in app.error)
        assert "Score ranges appear after the ranking request succeeds." in text
        assert "Recent matches appear after the ranking request succeeds." in text
        assert "<span class='column-value'>" not in text
        assert "<span class='legend-count'>" not in text
        assert "home-recent-job" not in text


def test_home_panels_keep_real_scores_and_open_the_existing_pages():
    from pages import _ring_tone

    assert _ring_tone(92) == "high"
    assert _ring_tone(80) == "high"
    assert _ring_tone(64) == "mid"
    assert _ring_tone(60) == "mid"
    assert _ring_tone(50) == "blue"
    assert _ring_tone(40) == "blue"
    assert _ring_tone(30) == "low"
    theme = Path(__file__).resolve().parents[0].joinpath("theme.py").read_text(encoding="utf-8")
    pages = Path(__file__).resolve().parents[0].joinpath("pages.py").read_text(encoding="utf-8")
    assert 'match_col, saved_col = st.columns(2, gap="large")' in pages
    assert "#20B8A0" in theme
    assert "#243656" not in theme
    assert "minmax(0, 1fr)" not in theme[theme.index(".home-match-card"):theme.index(".home-ring")]
    with _dashboard() as (app, _calls):
        text = _markdown(app)
        assert "<p class='section-label home-recent home-panel'>Recent matches</p>" in text
        assert "<p class='section-label home-saved home-panel'>Recently saved jobs</p>" in text
        assert text.count("<h3 class='match-title home-recent-job'>") == 3
        assert "home-ring-high" in text and "Score 92" in text
        assert "home-ring-mid" in text and "Score 64" in text
        assert "home-ring-low" in text and "Score 30" in text
        assert "<span class='home-chip'>SQL</span>" in text
        assert "Low Role" in text
        assert text.index("Top Role") < text.index("High Role") < text.index("Mid Role")
        app.session_state["matches"] = [
            {
                **match,
                "skill_score": match["total_score"],
                "role_score": 0,
                "location_score": 0,
                "explanation": "",
            }
            for match in app.session_state["matches"]
        ]
        next(button for button in app.button if button.key == "home-match-4").click().run()
        assert not app.exception, app.exception
        assert app.session_state["nav"] == "Match Insights"
        assert app.session_state["selected_match_id"] == 4
        assert app.session_state["match_choice"] == 4
        assert "Top Role" in _markdown(app)

    with _dashboard() as (app, _calls):
        next(button for button in app.button if button.key == "home-view-saved").click().run()
        assert not app.exception, app.exception
        assert app.session_state["nav"] == "Saved Jobs"
        assert "Saved Jobs" in " ".join(item.value for item in app.title)


def test_home_keeps_existing_scores_and_drops_unmatchable_listings():
    extra = {
        "job": {
            "id": 90,
            "title": "Hidden External Role",
            "company": "Adzuna Co",
            "is_matchable": False,
            "requirements_available": False,
        },
        "total_score": 30,
        "matched_skills": [],
        "semantic_matches": [],
        "missing_skills": [],
    }
    with _dashboard(matches=[*MATCHES, extra]) as (app, _calls):
        text = _markdown(app)
        assert _kpi(text, "Jobs matched") == "4"
        assert _kpi(text, "Average match score") == "49"
        assert "Hidden External Role" not in text
        assert "Score 92" in text
