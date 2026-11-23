"""Sample-data render of Match Insights. Every API call stays inside the mock."""

from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parent / "app.py"

SAMPLE_MATCHES = [
    {
        "job": {
            "id": 11,
            "title": "Frontend Engineer",
            "company": "Northwind",
            "location": "Remote",
        },
        "total_score": 64.43,
        "skill_score": 64.43,
        "role_score": 0,
        "location_score": 0,
        "matched_skills": ["Python"],
        "semantic_matches": [
            {
                "required_skill": "React",
                "candidate_skill": "React.js",
                "similarity": 0.9204,
            }
        ],
        "missing_skills": ["Tax Law"],
        "explanation": "Related frontend skills cover most of the role.",
    },
    {
        "job": {
            "id": 12,
            "title": "Exact Role",
            "company": "Contoso",
            "location": "London",
        },
        "total_score": 100,
        "skill_score": 70,
        "role_score": 20,
        "location_score": 10,
        "matched_skills": ["SQL"],
        "semantic_matches": [],
        "missing_skills": [],
        "explanation": "Every listed skill matches exactly.",
    },
]


class FakeResponse:
    """Stand-in for requests.Response, including the body attribute the client reads."""

    status_code = 200
    text = ""
    content = b'{"status":"ok"}'

    def json(self):
        return {"status": "ok", "message": "API is running."}


def test_match_insights_sample_cards_do_not_touch_the_api():
    """Render two sample cards and save one through the mock only."""
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append((method, url, kwargs.get("json")))
        return FakeResponse()

    def reject_session_request(*args, **kwargs):
        raise AssertionError("Session.request was called; the mock did not intercept it.")

    with (
        patch("requests.request", fake_request),
        patch("requests.sessions.Session.request", reject_session_request),
    ):
        app = AppTest.from_file(str(APP_PATH))
        app.session_state["auth_token"] = "test-token"
        app.session_state["candidate_id"] = 1
        app.session_state["candidate_name"] = "Sample Candidate"
        app.session_state["nav"] = "Match Insights"
        app.session_state["matches"] = SAMPLE_MATCHES
        app.run()

        assert not app.exception, app.exception
        markdown = "\n".join(item.value for item in app.markdown)
        assert markdown.count("<h3 class='match-title match-card'>") == 1
        assert "Exact Role" in markdown
        assert "Why this job matches" in markdown
        assert "Strong match" in markdown
        assert any(button.key == "match-prep-12" for button in app.button)
        assert "Every listed required skill is matched." in markdown
        assert "Skills, role, and location add up to the overall score." in markdown
        assert "It does not calculate or change the score." in markdown
        progress_text = " ".join(item.text or "" for item in app.progress)
        for expected in ("Total 100 / 100", "Skills 70 / 70", "Role 20 / 20", "Location 10 / 10"):
            assert expected in progress_text
        assert calls == [("GET", "http://127.0.0.1:8001/", None)]

        app.selectbox[0].set_value(11).run()
        assert not app.exception, app.exception
        switched = "\n".join(item.value for item in app.markdown)
        assert "Frontend Engineer" in switched
        assert "Good match" in switched
        assert "React · your skill React.js · 92.04%" in switched
        assert ">Semantic matches<" in switched
        assert "Tax Law" in switched
        assert "These required skills are not matched yet" in switched
        assert "Skills, role, and location add up to the overall score." in switched
        switched_progress = " ".join(item.text or "" for item in app.progress)
        for expected in ("Total 64.43 / 100", "Skills 64.43 / 70", "Role 0 / 20", "Location 0 / 10"):
            assert expected in switched_progress

        next(button for button in app.button if button.key == "save-11").click().run()
        assert not app.exception, app.exception
        assert [item.value for item in app.success] == ["Saved Frontend Engineer."]
        next(button for button in app.button if button.key == "match-prep-11").click().run()
        assert app.session_state["nav"] == "Discover Jobs"
        assert app.session_state["selected_job_id"] == 11

    assert ("POST", "http://127.0.0.1:8001/jobs/11/save", {"candidate_id": 1}) in calls
    assert all(method == "GET" or method == "POST" for method, _, _ in calls)
    assert sum(method == "POST" for method, _, _ in calls) == 1


def test_match_insights_hides_unmatchable_listings():
    """A stored score on an unmatchable job is not shown beside real rankings."""
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append((method, url, kwargs.get("json")))
        return FakeResponse()

    hidden = {
        "job": {
            "id": 90,
            "title": "Hidden External Role",
            "company": "Adzuna Co",
            "location": "London",
            "is_matchable": False,
            "requirements_available": False,
            "matchability_status": "unmatchable",
        },
        "total_score": 30,
        "skill_score": 0,
        "role_score": 20,
        "location_score": 10,
        "matched_skills": [],
        "semantic_matches": [],
        "missing_skills": [],
        "explanation": "This score must not be shown.",
    }

    def reject_session_request(*args, **kwargs):
        raise AssertionError("Session.request was called; the mock did not intercept it.")

    with (
        patch("requests.request", fake_request),
        patch("requests.sessions.Session.request", reject_session_request),
    ):
        app = AppTest.from_file(str(APP_PATH))
        app.session_state["auth_token"] = "test-token"
        app.session_state["candidate_id"] = 1
        app.session_state["candidate_name"] = "Sample Candidate"
        app.session_state["nav"] = "Match Insights"
        app.session_state["matches"] = [*SAMPLE_MATCHES, hidden]
        app.run()

        assert not app.exception, app.exception
        text = "\n".join(item.value for item in app.markdown)
        assert "Exact Role" in text
        assert "Hidden External Role" not in text
        assert "This score must not be shown." not in text
        options = " ".join(str(option) for option in app.selectbox[0].options)
        assert "Hidden External Role" not in options

    assert calls == [("GET", "http://127.0.0.1:8001/", None)]


def test_match_insights_keeps_returned_facts_and_actions():
    """Show provider facts that exist, and do not offer a save for a live Jooble id."""
    adzuna = {
        "job": {
            "id": 21,
            "title": "Platform Engineer",
            "company": "Fabrikam",
            "location": "Bengaluru",
            "description": "Build the listing services.",
            "source": "adzuna",
            "source_country": "in",
            "source_url": "https://www.adzuna.in/details/21",
            "category_label": "IT Jobs",
            "salary_min": 900000,
            "salary_currency": "INR",
            "contract_time": "full_time",
            "workplace": "remote",
            "min_experience": 2,
            "posted_at": "2026-11-22T08:00:00",
        },
        "total_score": 40,
        "skill_score": 20,
        "role_score": 10,
        "location_score": 10,
        "matched_skills": ["Python"],
        "semantic_matches": [],
        "missing_skills": ["Go"],
        "unused_candidate_skills": ["SQL"],
        "explanation": "",
    }
    jooble = {
        "job": {
            "id": "jooble-in-1",
            "title": "Live Engineer",
            "company": "",
            "location": "Mumbai",
            "source": "jooble",
            "source_country": "in",
            "source_url": "https://in.jooble.org/jdp/21",
            "description_is_snippet": True,
            "description": "A short live snippet.",
        },
        "total_score": 15,
        "skill_score": 15,
        "location_score": 0,
        "matched_skills": [],
        "semantic_matches": [],
        "missing_skills": [],
        "explanation": "Live explanation.",
    }
    mismatch = {
        "job": {"id": 22, "title": "Mismatch Role", "company": "Contoso", "location": "London"},
        "total_score": 40,
        "skill_score": 10,
        "role_score": 10,
        "location_score": 10,
        "matched_skills": [],
        "semantic_matches": [],
        "missing_skills": [],
        "explanation": "Returned total stays 40.",
    }
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append((method, url, kwargs.get("json")))
        return FakeResponse()

    def reject_session_request(*args, **kwargs):
        raise AssertionError("Session.request was called; the mock did not intercept it.")

    with (
        patch("requests.request", fake_request),
        patch("requests.sessions.Session.request", reject_session_request),
    ):
        app = AppTest.from_file(str(APP_PATH))
        app.session_state["auth_token"] = "test-token"
        app.session_state["candidate_id"] = 1
        app.session_state["candidate_name"] = "Sample Candidate"
        app.session_state["nav"] = "Match Insights"
        app.session_state["matches"] = [adzuna, jooble, mismatch]
        app.session_state["saved_jobs"] = [{"id": 3, "job": {"id": 21}}]
        app.run()

        assert not app.exception, app.exception
        text = "\n".join(item.value for item in app.markdown)
        assert "Platform Engineer" in text
        assert "Country: India" in text
        assert "Industry: IT Jobs" in text
        assert "Salary: 900000 INR" in text
        assert "Employment type: Full-time" in text
        assert "Work arrangement: Remote" in text
        assert "https://www.adzuna.in/" in text
        assert "View original listing" in text
        assert "No explanation was returned for this job." in text
        assert "Other profile skills" in text
        assert ">SQL<" in text
        assert any(button.label == "Saved" and button.disabled for button in app.button)
        assert not any(button.key == "save-21" for button in app.button)
        progress = " ".join(item.text or "" for item in app.progress)
        assert "Total 40 / 100" in progress
        assert "Skills 20 / 70" in progress
        assert "Role 10 / 20" in progress
        assert "Location 10 / 10" in progress
        assert "Skills, role, and location add up to the overall score." in text

        app.selectbox[0].set_value("jooble-in-1").run()
        live = "\n".join(item.value for item in app.markdown)
        assert "Live Engineer" in live
        assert "https://in.jooble.org/" in live
        assert "Company not provided" in live
        assert "description snippet" in live
        assert any("Live results are not stored." in item.value for item in app.caption)
        assert not any(str(button.key).startswith("save-") for button in app.button)
        assert not any(str(button.key).startswith("match-prep-") for button in app.button)
        live_progress = " ".join(item.text or "" for item in app.progress)
        assert "Role " not in live_progress
        assert "Total 15 / 100" in live_progress
        assert "Skills, role, and location add up to the overall score." not in live
        assert "Salary:" not in live

        app.selectbox[0].set_value(22).run()
        mixed = "\n".join(item.value for item in app.markdown)
        assert ">40<" in mixed
        assert "The overall score shown is the total returned for this job." in mixed
        mixed_progress = " ".join(item.text or "" for item in app.progress)
        assert "Total 40 / 100" in mixed_progress
        assert "Total 30 / 100" not in mixed_progress

    assert not any(method == "POST" for method, _, _ in calls)


def test_match_styles_use_theme_tokens():
    css = (Path(__file__).resolve().parent / "theme.py").read_text(encoding="utf-8")
    page = (Path(__file__).resolve().parent / "pages.py").read_text(encoding="utf-8")
    assert "match-page" in page
    assert ".main:has(.match-page)" in css
    assert "var(--accent-text)" in css
    assert "var(--lavender)" in css
    assert "skill-heading" in css
    assert "@media (max-width: 680px)" in css
