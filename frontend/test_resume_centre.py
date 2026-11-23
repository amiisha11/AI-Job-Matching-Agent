"""Resume Centre with a mocked API. The sample resume is synthetic."""

import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

FRONTEND_DIR = Path(__file__).resolve().parent
BACKEND_DIR = FRONTEND_DIR.parent / "backend"
for folder in (FRONTEND_DIR, BACKEND_DIR):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from services.resume_match import match_resume_to_job
from test_auth_flow import SECRET, _labeled, _mocked_auth
from test_home_profile_saved import FakeResponse, _markdown

APP_PATH = FRONTEND_DIR / "app.py"
EMAIL = "ada.example@example.com"
RESUME_TEXT = f"""
Example Candidate
{EMAIL}
+1 415 555 0134

Professional summary
Analyst who builds reports and reviews data quality for operations teams across weekly cycles.

Skills
Python, SQL, Excel

Work experience
Improved report delivery by 20% for the finance team.

Education
B.Tech in Computer Science, Example University

Projects
Built a dashboard project using Python and SQL to track weekly orders.
"""
HEALTH = {
    "score": 63,
    "passed": 5,
    "total": 8,
    "formula": "Each of the 8 checks counts equally. This is not a claim that the resume will pass every applicant tracking system.",
    "checks": [
        {"key": "contact", "label": "Contact information", "status": "found", "detail": "An email address or phone number was found."},
        {"key": "projects", "label": "Projects", "status": "missing", "detail": "Leave it out only when work experience already shows the same evidence."},
    ],
    "suggestions": ["Add a skills section that lists tools and skills your experience supports."],
}
JOB = {
    "id": 11,
    "title": "Data Analyst",
    "company": "Northwind",
    "location": "Remote",
    "description": "Prepare dashboards and analyze operational data.",
    "required_skills": ["Python", "SQL", "Tableau"],
    "min_experience": 2,
}
PROFILE = {
    "id": 4,
    "name": "Ada Lovelace",
    "email": "ada@example.com",
    "education": "Mathematics",
    "skills": ["Python"],
    "preferred_roles": ["Analyst"],
    "preferred_locations": ["London"],
    "years_experience": 3,
}


class StatusResponse(FakeResponse):
    def __init__(self, payload, status_code=200):
        super().__init__(payload)
        self.status_code = status_code
        self.content = b"{}" if status_code < 400 else b'{"detail":"error"}'


@contextmanager
def _resume_app(**state):
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append((method, url, kwargs.get("json"), kwargs.get("files")))
        if method == "GET" and url.endswith(":8001/"):
            return StatusResponse({"status": "ok", "message": "API is running."})
        if method == "GET" and url.endswith("/jobs/"):
            if state.get("jobs_fail"):
                return StatusResponse({"detail": "The job list could not be read."}, 500)
            return StatusResponse(state.get("jobs", [JOB]))
        if method == "POST" and url.endswith("/resume/extract"):
            if state.get("extract_error"):
                return StatusResponse({"detail": state["extract_error"]}, 422)
            upload = kwargs["files"]["file"]
            if not upload[1].startswith(b"%PDF"):
                return StatusResponse({"detail": "This file is not a PDF."}, 422)
            assert upload[0].lower().endswith(".pdf")
            return StatusResponse(
                {
                    "filename": "synthetic.pdf",
                    "status": "extracted",
                    "message": "Text extracted from synthetic.pdf.",
                    "page_count": 1,
                    "character_count": 1200,
                    "text": RESUME_TEXT,
                    "health": HEALTH,
                }
            )
        if method == "POST" and url.endswith("/resume/match"):
            if state.get("match_error"):
                return StatusResponse({"detail": state["match_error"]}, 422)
            assert kwargs["json"]["text"] == RESUME_TEXT
            assert kwargs["json"]["job_id"] == 11
            if state.get("match_payload") is not None:
                return StatusResponse(state["match_payload"])
            return StatusResponse(match_resume_to_job(RESUME_TEXT, type("Job", (), JOB)))
        raise AssertionError(f"Unexpected API call {method} {url}")

    def reject_session_request(*args, **kwargs):
        raise AssertionError("Session.request was called; the mock did not intercept it.")

    with (
        patch("requests.request", fake_request),
        patch("requests.sessions.Session.request", reject_session_request),
    ):
        app = AppTest.from_file(str(APP_PATH))
        app.session_state["nav"] = "Resume Centre"
        app.session_state["auth_token"] = "test-token"
        app.session_state["candidate_id"] = 4
        app.session_state["candidate_name"] = "Ada Lovelace"
        app.session_state["profile"] = PROFILE
        for key, value in state.items():
            if key not in {"jobs", "jobs_fail", "extract_error", "match_error", "match_payload"}:
                app.session_state[key] = value
        app.run()
        assert not app.exception, app.exception
        yield app, calls


def test_empty_resume_page_explains_privacy_and_does_not_invent_a_score():
    with _resume_app() as (app, calls):
        text = _markdown(app)
        assert "Review your resume or compare it with a job opportunity." in text
        assert "Your original PDF isn't stored." in text
        assert "The full resume is not sent to an external AI service." in text
        assert "Signed in as" not in text
        assert "Step 1 — Upload your resume" not in text
        assert "<p class='section-label resume-empty'>No resume uploaded</p>" in text
        assert "<p class='resume-percent'>" not in text
        assert app.file_uploader[0].proto.max_upload_size_mb == 5
        assert not any(call[0] == "POST" for call in calls)
        _labeled(app.radio, "Choose a step").set_value("Match My Resume to a Job").run()
        assert "<p class='section-label resume-match-empty'>Upload a resume first</p>" in _markdown(app)


def test_upload_shows_real_status_and_clear_removes_it():
    with _resume_app() as (app, calls):
        assert app.file_uploader[0].allowed_type == [".pdf"]
        app.file_uploader[0].set_value(("resume.pdf", b"not a pdf", "application/pdf")).run()
        assert any("not a PDF" in item.value for item in app.error)
        assert app.session_state["resume"] is None

        app.file_uploader[0].set_value(("synthetic.pdf", b"%PDF-1.4 synthetic", "application/pdf")).run()
        text = _markdown(app)
        assert "<p class='match-title resume-filename'>synthetic.pdf</p>" in text
        assert "Text extracted from synthetic.pdf." in text
        assert "Needs a little improvement" in text
        assert "<p class='resume-percent'>63%</p>" in text
        assert "5 of 8 checks passed" in text
        assert "applicant tracking" in text
        assert "Present in your resume" in text
        assert "Could be improved" in text
        assert "My Resume Improvement Checklist" in text
        assert "0 of " in text and " improvements completed" in text
        assert EMAIL not in text
        assert any(url.endswith("/resume/extract") for _, url, _, _ in calls)

        _labeled(app.checkbox, "Make my project descriptions clearer.").set_value(True).run()
        assert "1 of " in _markdown(app)

        app.file_uploader[0].set_value(("revised.pdf", b"%PDF-1.4 revised", "application/pdf")).run()
        assert app.session_state["resume"]["filename"] == "synthetic.pdf"
        assert app.session_state["resume_match"] is None
        assert sum(url.endswith("/resume/extract") for _, url, _, _ in calls) == 3
        assert calls[-1][3]["file"][1].startswith(b"%PDF-1.4 revised")

        _labeled(app.button, "Clear resume").click().run()
        assert app.session_state["resume"] is None
        assert app.session_state["resume_match"] is None
        assert "<p class='section-label resume-empty'>No resume uploaded</p>" in _markdown(app)


def test_job_match_shows_coverage_and_does_not_treat_a_missing_skill_as_possessed():
    with _resume_app(resume={"filename": "synthetic.pdf", "message": "Text extracted.", "text": RESUME_TEXT, "health": HEALTH, "page_count": 1, "character_count": 1200}, job_catalog=[JOB]) as (app, _calls):
        _labeled(app.radio, "Choose a step").set_value("Match My Resume to a Job").run()
        assert _labeled(app.selectbox, "Job").value.startswith("Data Analyst")
        _labeled(app.button, "Analyze Resume for This Job").click().run()
        text = _markdown(app)
        assert "<p class='resume-percent resume-metric-value'>67%</p>" in text
        assert "Required Skill Coverage" in text
        assert "does not guarantee interview selection" in text
        assert "Relevant skills" in text
        assert "Exact matches" in text
        assert "Missing skills" in text
        assert "chip-exact" in text and "Python" in text
        assert "chip-missing" in text and "Tableau" in text
        assert "Do not add Tableau" in text
        assert "The resume text includes Python." in text
        assert EMAIL not in text
        assert "total_score" not in text

    related_payload = {
        "job_id": 11,
        "title": "Data Analyst",
        "company": "Northwind",
        "location": "Remote",
        "coverage_percent": 67,
        "found_count": 2,
        "required_count": 3,
        "found_skills": ["Python", "SQL"],
        "missing_skills": ["Tableau"],
        "related_skills": [
            {"resume_skill": "Data visualization", "required_skill": "Tableau", "similarity": 0.81}
        ],
        "strengths": ["The resume text includes Python."],
        "suggestions": [],
        "gaps": ["Do not add Tableau unless your own experience supports it."],
    }
    with _resume_app(
        resume={"filename": "synthetic.pdf", "text": RESUME_TEXT, "health": HEALTH},
        job_catalog=[JOB],
        match_payload=related_payload,
    ) as (related, _calls):
        _labeled(related.radio, "Choose a step").set_value("Match My Resume to a Job").run()
        _labeled(related.button, "Analyze Resume for This Job").click().run()
        related_text = _markdown(related)
        assert "class='chip chip-semantic'>Data visualization" in related_text
        assert "is related to Tableau." in related_text
        assert "This is not counted as the required skill." in related_text

    with _resume_app(
        resume={"filename": "synthetic.pdf", "text": RESUME_TEXT, "health": HEALTH},
        job_catalog=[JOB],
        match_error="The resume could not be compared with that job.",
        resume_match={"job_id": 11, "coverage_percent": 67},
    ) as (failed, _calls):
        _labeled(failed.radio, "Choose a step").set_value("Match My Resume to a Job").run()
        _labeled(failed.button, "Analyze Resume for This Job").click().run()
        assert failed.session_state["resume_match"] is None
        assert any("could not be compared" in item.value for item in failed.error)
        assert "67%" not in _markdown(failed)

    with _resume_app(resume={"filename": "synthetic.pdf", "text": RESUME_TEXT, "health": HEALTH}, job_catalog=[]) as (empty, _calls):
        _labeled(empty.radio, "Choose a step").set_value("Match My Resume to a Job").run()
        assert "<p class='section-label resume-jobs-empty'>No jobs are stored yet</p>" in _markdown(empty)

    with _resume_app(resume={"filename": "synthetic.pdf", "text": RESUME_TEXT, "health": HEALTH}, jobs_fail=True) as (broken, _calls):
        _labeled(broken.radio, "Choose a step").set_value("Match My Resume to a Job").run()
        assert any("could not be read" in item.value for item in broken.error)


def test_logout_and_login_clear_the_session_resume():
    seeded = {"filename": "synthetic.pdf", "text": RESUME_TEXT}
    with _mocked_auth(
        "Home",
        auth_token="issued-token",
        candidate_id=9,
        candidate_name="Ada Lovelace",
        profile={"id": 9, "name": "Ada Lovelace", "email": "ada@example.com"},
        resume=seeded,
        resume_match={"job_id": 11},
    ) as (home, _calls):
        assert any(button.label == "Resume Centre" for button in home.button)
        assert EMAIL not in _markdown(home)
        _labeled(home.button, "Log out").click().run()
        assert home.session_state["resume"] is None
        assert home.session_state["resume_match"] is None
        assert EMAIL not in " ".join(str(home.session_state[key]) for key in home.session_state)

    with _mocked_auth("Login", resume=seeded) as (login, _calls):
        _labeled(login.text_input, "Email").set_value("ada@example.com")
        _labeled(login.text_input, "Password").set_value(SECRET)
        _labeled(login.button, "Log in").click().run()
        assert login.session_state["auth_token"] == "issued-token"
        assert login.session_state["resume"] is None
        assert login.session_state["resume_notice"] is None


def test_invalid_and_oversized_pdfs_are_rejected_before_upload():
    with _resume_app() as (app, calls):
        assert app.file_uploader[0].allowed_type == [".pdf"]
        app.file_uploader[0].set_value(("notes.pdf", b"not a pdf", "application/pdf")).run()
        assert any("not a PDF" in item.value for item in app.error)
        assert app.session_state["resume"] is None
        assert app.session_state["resume_notice"] is None
        assert any(url.endswith("/resume/extract") for _, url, _, _ in calls)

    with _resume_app() as (large, calls):
        payload = b"%PDF" + b"x" * ((5 * 1024 * 1024) - 3)
        large.file_uploader[0].set_value(("large.pdf", payload, "application/pdf")).run()
        assert any("5 MB" in item.value for item in large.error)
        assert large.session_state["resume"] is None
        assert large.session_state["resume_notice"] is None
        assert not any(url.endswith("/resume/extract") for _, url, _, _ in calls)
        assert "Selected file: large.pdf" in _markdown(large)


def test_extract_failure_does_not_confirm_an_upload():
    with _resume_app(extract_error="This PDF could not be read. It may be corrupted.") as (app, calls):
        app.file_uploader[0].set_value(("broken.pdf", b"%PDF-1.4 broken", "application/pdf")).run()
        assert app.session_state["resume"] is None
        assert any("could not be read" in item.value for item in app.error)
        assert not any(getattr(item, "value", "") == "The PDF was read for this session. The original file was not stored." for item in app.success)
        assert any(url.endswith("/resume/extract") for _, url, _, _ in calls)


def test_missing_report_fields_do_not_invent_scores_or_skills():
    sparse = {
        "filename": "synthetic.pdf",
        "message": "Text extracted.",
        "text": RESUME_TEXT,
        "page_count": 1,
        "character_count": 40,
        "health": {"formula": "The checklist explanation was not returned."},
    }
    with _resume_app(resume=sparse) as (app, _calls):
        text = _markdown(app)
        assert "Health check unavailable" in text
        assert "<p class='resume-percent'>" not in text
        assert "No checklist items were returned." in text
        assert "My Resume Improvement Checklist" in text
        assert "No improvement items came from this resume." in text
        assert EMAIL not in text

    payload = {
        "job_id": 11,
        "title": "Data Analyst",
        "company": "Northwind",
        "location": "Remote",
        "coverage_percent": None,
        "found_skills": [],
        "missing_skills": [],
        "related_skills": [],
        "strengths": [],
        "suggestions": [],
        "gaps": [],
        "keywords_found": [],
        "keywords_missing": [],
    }
    with _resume_app(
        resume={"filename": "synthetic.pdf", "text": RESUME_TEXT, "health": HEALTH},
        job_catalog=[JOB],
        match_payload=payload,
    ) as (matched, _calls):
        _labeled(matched.radio, "Choose a step").set_value("Match My Resume to a Job").run()
        _labeled(matched.button, "Analyze Resume for This Job").click().run()
        text = _markdown(matched)
        assert "<p class='resume-percent resume-metric-value'>—</p>" in text
        assert "No required-skill comparison was returned." in text
        assert "Your Strengths" not in text
        assert "How to Improve" not in text
        assert 'class="chip chip-exact"' not in text
        assert "Exact matches" not in text
        assert "Missing skills" not in text
        assert EMAIL not in text
        assert "applicant tracking score" in text


def test_resume_centre_styles_follow_the_shared_tokens():
    css = (FRONTEND_DIR / "theme.py").read_text(encoding="utf-8")
    assert "resume-page" in css
    assert "background: var(--surface)" in css
    assert "color: var(--ink)" in css
    assert "color: var(--text-secondary)" in css
    assert "var(--resume-found-bg)" in css
    assert "#6D62C8" not in css
    assert "#F4F2FB" not in css
    source = (FRONTEND_DIR / "resume_centre.py").read_text(encoding="utf-8")
    assert "resume[\"text\"]" not in source
    assert "st.write(resume" not in source
