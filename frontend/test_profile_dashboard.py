"""Profile dashboard figures from saved profile fields. No database writes."""

import json
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

FRONTEND_DIR = Path(__file__).resolve().parent
if str(FRONTEND_DIR) not in sys.path:
    sys.path.insert(0, str(FRONTEND_DIR))

from profile_metrics import completion_percent, experience_text, profile_sections
from test_home_profile_saved import APP_PATH, _markdown

FULL_PROFILE = {
    "id": 4,
    "name": "Ada Lovelace",
    "email": "ada@example.com",
    "education": "Mathematics",
    "skills": ["Python", "SQL"],
    "preferred_roles": ["Data Analyst"],
    "preferred_locations": ["London"],
    "years_experience": 3,
}


def _sections(profile: dict) -> dict[str, bool]:
    return {item["label"]: item["complete"] for item in profile_sections(profile)}


def test_completion_uses_only_saved_fields():
    contact_only = {"name": "Ada", "email": "ada@example.com"}
    assert _sections(contact_only) == {
        "Contact details": True,
        "Education and background": False,
        "Skills": False,
        "Career preferences": False,
        "Location preferences": False,
        "Experience": False,
    }
    assert completion_percent(profile_sections(contact_only)) == 17

    partial = {
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "education": None,
        "skills": ["  "],
        "preferred_roles": [],
        "preferred_locations": [],
        "years_experience": 0,
    }
    assert _sections(partial)["Experience"] is True
    assert _sections(partial)["Skills"] is False
    assert _sections(partial)["Education and background"] is False
    assert completion_percent(profile_sections(partial)) == 33
    assert experience_text(0) == "Less than 1 year"
    assert experience_text(True) is None
    assert _sections({"education": "Not specified", "years_experience": "3"})["Education and background"] is False
    assert _sections({"education": "Not specified", "years_experience": "3"})["Experience"] is False
    guided = {
        "name": "Ada",
        "email": "ada@example.com",
        "preferred_industries": ["it-jobs"],
        "preferred_countries": ["in"],
        "years_experience": 0,
    }
    guided_sections = profile_sections(guided)
    filled = sum(1 for section in guided_sections if section["complete"])
    assert filled == 4
    assert completion_percent(guided_sections) == round(100 * filled / len(guided_sections))

    complete = dict(FULL_PROFILE)
    assert completion_percent(profile_sections(complete)) == 100
    blank = {
        "name": " ",
        "email": "not-an-email",
        "education": "",
        "skills": [],
        "preferred_roles": [],
        "preferred_locations": [],
        "years_experience": None,
    }
    assert completion_percent(profile_sections(blank)) == 0


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.status_code = status_code
        self.content = b"" if status_code == 204 else json.dumps(payload).encode()
        self._payload = payload

    def json(self):
        return self._payload


@contextmanager
def _profile_app(profile=None, patch_status=200, patch_body=None, confirm_status=200, confirm_body=None):
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append((method, url, kwargs.get("json")))
        if method == "PATCH" and "/candidates/" in url:
            if patch_status >= 400:
                return FakeResponse({"detail": patch_body or "Could not save the profile."}, patch_status)
            body = kwargs["json"]
            return FakeResponse(
                {
                    "id": 4,
                    "name": body["name"],
                    "email": body["email"],
                    "education": body["education"],
                    "skills": body["skills"],
                    "preferred_roles": body["preferred_roles"],
                    "preferred_locations": body["preferred_locations"],
                    "years_experience": body["years_experience"],
                }
            )
        if method == "GET" and url.endswith("/jobs/filters"):
            return FakeResponse({"categories": [], "countries": [], "category_status": "ready"})
        if method == "GET" and url.split("?")[0].endswith("/jobs/"):
            return FakeResponse([])
        if method == "GET" and url.endswith("/candidates/4"):
            if confirm_status >= 400:
                return FakeResponse({"detail": confirm_body or "Could not read the profile."}, confirm_status)
            return FakeResponse(confirm_body)
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
        app.session_state["nav"] = "My Profile"
        app.session_state["auth_token"] = "test-token"
        app.session_state["candidate_id"] = 4
        app.session_state["candidate_name"] = "Ada Lovelace"
        app.session_state["profile"] = profile
        app.run()
        assert not app.exception, app.exception
        yield app, calls


def test_profile_dashboard_shows_the_saved_profile():
    with _profile_app(FULL_PROFILE) as (app, calls):
        text = _markdown(app)
        assert "<p class='section-label profile-overview'>Candidate Profile</p>" in text
        assert "ada@example.com" in text
        assert "<p class='profile-percent'>100%</p>" in text
        assert "Education: Mathematics" in text
        assert "Years of experience: 3 years" in text
        assert '<span class="chip chip-exact">Python</span>' in text
        assert '<span class="chip chip-semantic">London</span>' in text
        assert "How is profile completion calculated?" in [item.label for item in app.expander]
        assert "<p class='hero-lead'>Six sections are counted" not in text
        assert "divided by six" in text
        assert text.count("<li>Contact details</li>") == 1
        assert "Categories and proficiency levels are not stored" in text
        assert "Beginner" not in text
        assert any(button.label == "Save Changes" for button in app.button)
        assert any(button.label == "Cancel" for button in app.button)
        assert _labeled(app.multiselect, "Skills").label == "Skills"
        assert not any("/candidates/" in url for _, url, _ in calls)


def test_partial_profile_keeps_the_blank_sections_visible():
    partial = {
        "id": 4,
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "education": None,
        "skills": [],
        "preferred_roles": [],
        "preferred_locations": [],
        "years_experience": 0,
    }
    with _profile_app(partial) as (app, _calls):
        text = _markdown(app)
        assert "<p class='profile-percent'>33%</p>" in text
        assert "2 of 6 sections filled" in text
        assert "Education: Not specified" in text
        assert "Years of experience: Less than 1 year" in text
        assert "No skills saved yet." in text
        assert "<span class='completion-name'>Contact details</span><span class='completion-state'>Filled</span>" in text
        assert "<span class='completion-name'>Education and background</span><span class='completion-state'>Not saved</span>" in text
        assert "completion-open" in text
        assert "<span class='completion-name'>Skills</span><span class='completion-state'>Not saved</span>" in text
        assert "<span class='completion-name'>Experience</span><span class='completion-state'>Filled</span>" in text
        assert "completion-grid" in text


def test_missing_profile_does_not_invent_a_percentage():
    with _profile_app(None) as (app, calls):
        text = _markdown(app)
        assert "percentage stays hidden" in text
        assert "<span class='ring-label'>" not in text
        assert any(button.label == "Save Changes" for button in app.button)
        assert not any(url.endswith("/candidates/4") for _, url, _ in calls)


def test_cancel_restores_the_saved_profile_without_a_request():
    with _profile_app(FULL_PROFILE) as (app, calls):
        _labeled(app.text_input, "Name").set_value("Grace Hopper")
        _labeled(app.button, "Remove Python").click().run()
        assert _labeled(app.multiselect, "Skills").value == ["SQL"]
        _labeled(app.button, "Cancel").click().run()
        assert _labeled(app.text_input, "Name").value == "Ada Lovelace"
        assert _labeled(app.multiselect, "Skills").value == ["Python", "SQL"]
        assert any("Edits discarded." in item.value for item in app.info)
        assert not any(method == "PATCH" for method, _, _ in calls)


def test_profile_save_error_leaves_the_stored_profile_unchanged():
    with _profile_app(FULL_PROFILE, patch_status=409, patch_body="Email stays the address you used to sign up.") as (
        app,
        calls,
    ):
        _labeled(app.text_input, "Name").set_value("Grace Hopper")
        _labeled(app.button, "Save Changes").click().run()
        assert any("Email stays the address you used to sign up." in item.value for item in app.error)
        assert not app.success
        assert app.session_state["profile"]["name"] == "Ada Lovelace"
        assert any(method == "PATCH" for method, _, _ in calls)
        assert not any(method == "POST" for method, _, _ in calls)


def test_confirm_error_keeps_the_saved_response_and_explains_the_failure():
    with _profile_app(FULL_PROFILE, confirm_status=500, confirm_body="Could not read the profile.") as (app, calls):
        _labeled(app.text_input, "Name").set_value("Grace Hopper")
        _labeled(app.button, "Save Changes").click().run()
        assert any("Could not read the profile." in item.value for item in app.warning)
        assert any("Profile saved." in item.value for item in app.success)
        assert "Grace Hopper" in _markdown(app)
        assert sum(method == "GET" and url.endswith("/candidates/4") for method, url, _ in calls) == 1


def _labeled(widgets, label):
    return next(widget for widget in widgets if widget.label == label)
