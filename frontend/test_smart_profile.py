"""Guided profile builder checks. No live database writes."""

import json
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

FRONTEND_DIR = Path(__file__).resolve().parent
if str(FRONTEND_DIR) not in sys.path:
    sys.path.insert(0, str(FRONTEND_DIR))

from profile_builder import dedupe_items, profile_payload
from test_home_profile_saved import APP_PATH, _labeled, _markdown

FILTERS = {
    "categories": [
        {"value": "it-jobs", "label": "IT Jobs"},
        {"value": "legal-jobs", "label": "Legal Jobs"},
    ],
    "countries": [
        {"value": "gb", "label": "United Kingdom"},
        {"value": "in", "label": "India"},
    ],
    "category_status": "ready",
}


def test_education_degree_and_custom_field_are_optional():
    payload, error = profile_payload(
        "Ada Lovelace",
        "Ada@Example.com",
        "Not specified",
        "",
        ["Python"],
        ["Analyst"],
        ["London"],
        2,
        degree_choice="Other",
        custom_degree="  Licentiate  ",
        field_choice="Other",
        custom_field="Logic",
        institution="City College",
        graduation_year="2020",
    )
    assert error is None
    assert payload["education"] == "Licentiate"
    assert payload["degree"] == "Licentiate"
    assert payload["field_of_study"] == "Logic"
    assert payload["institution"] == "City College"
    assert payload["graduation_year"] == 2020
    assert payload["email"] == "ada@example.com"

    kept, error = profile_payload(
        "Ada Lovelace",
        "ada@example.com",
        "B.Tech",
        "",
        ["Python"],
        [],
        [],
        0,
        degree_choice="M.Sc.",
    )
    assert error is None
    assert kept["education"] == "B.Tech"
    assert kept["degree"] == "M.Sc."
    blank, blank_error = profile_payload(
        "Ada",
        "ada@example.com",
        "Not specified",
        "",
        [],
        [],
        [],
        0,
        graduation_year="year",
    )
    assert blank is None
    assert "Graduation year" in blank_error


def test_skills_roles_and_locations_drop_case_and_space_duplicates():
    assert dedupe_items([" Python ", "python", "SQL", " sql "]) == ["Python", "SQL"]
    payload, error = profile_payload(
        "Ada",
        "ada@example.com",
        "B.Tech",
        "",
        [" Python ", "python", "SQL"],
        [" Analyst ", "analyst"],
        [" London ", "london"],
        1,
        preferred_industries=["it-jobs", " IT-jobs "],
        preferred_countries=["in", " IN "],
        remote_choice="Remote",
    )
    assert error is None
    assert payload["skills"] == ["Python", "SQL"]
    assert payload["preferred_roles"] == ["Analyst"]
    assert payload["preferred_locations"] == ["London"]
    assert payload["preferred_industries"] == ["it-jobs"]
    assert payload["preferred_countries"] == ["in"]
    assert payload["remote_preference"] == "remote"


class FakeResponse:
    def __init__(self, payload):
        self.status_code = 200
        self.content = json.dumps(payload).encode()
        self._payload = payload

    def json(self):
        return self._payload


@contextmanager
def _builder(profile):
    calls = []
    saved = {}

    def fake_request(method, url, **kwargs):
        calls.append((method, url, kwargs.get("json")))
        if method == "PATCH" and "/candidates/4" in url:
            saved.clear()
            saved.update(kwargs["json"])
            return FakeResponse({"id": 4, **saved})
        if method == "GET" and url.endswith("/candidates/4"):
            return FakeResponse({"id": 4, **saved})
        if method == "GET" and url.endswith("/jobs/filters"):
            return FakeResponse(FILTERS)
        if method == "GET" and url.split("?")[0].endswith("/jobs/"):
            return FakeResponse(
                [
                    {"id": 1, "title": "Ward Nurse", "required_skills": ["Patient care", "Python"]},
                    {"id": 2, "title": "Legal Associate", "required_skills": ["Legal research"]},
                ]
            )
        if method == "GET" and url.endswith(":8001/"):
            return FakeResponse({"status": "ok", "message": "API is running."})
        raise AssertionError(f"Unexpected API call {method} {url}")

    with (
        patch("requests.request", fake_request),
        patch("requests.sessions.Session.request", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("session"))),
    ):
        app = AppTest.from_file(str(APP_PATH))
        app.session_state["nav"] = "My Profile"
        app.session_state["auth_token"] = "test-token"
        app.session_state["candidate_id"] = 4
        app.session_state["profile"] = profile
        app.run()
        assert not app.exception, app.exception
        yield app, calls


def test_builder_saves_industries_countries_and_keeps_existing_skills():
    profile = {
        "id": 4,
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "education": "Mathematics",
        "skills": ["Python", "SQL"],
        "preferred_roles": ["Data Analyst"],
        "preferred_locations": ["London"],
        "years_experience": 3,
    }
    with _builder(profile) as (app, calls):
        _labeled(app.text_input, "Name").set_value("Ada Lovelace")
        _labeled(app.button, "Save Changes").click().run()
        first = [call for call in calls if call[0] == "PATCH"][-1][2]
        assert first["skills"] == ["Python", "SQL"]
        assert first["education"] == "Mathematics"
        assert first["preferred_roles"] == ["Data Analyst"]
        assert first["preferred_locations"] == ["London"]

        _labeled(app.button, "Continue").click().run()
        assert "Ward Nurse" not in _markdown(app)
        assert "Patient care" in _labeled(app.multiselect, "Skills").options
        _labeled(app.button, "Remove selected skills").click().run()
        assert _labeled(app.multiselect, "Skills").value == []
        _labeled(app.multiselect, "Skills").select("Python").select("Patient care")
        _labeled(app.button, "Continue").click().run()
        assert "Ward Nurse" in _labeled(app.multiselect, "Preferred roles").options
        assert "Legal Associate" in _labeled(app.multiselect, "Preferred roles").options
        _labeled(app.multiselect, "Preferred industries").select("it-jobs").select("legal-jobs")
        _labeled(app.text_input, "Add a role").set_value("  ward nurse  ")
        _labeled(app.button, "Add role").click().run()
        roles = _labeled(app.multiselect, "Preferred roles").value
        assert sum(item.casefold() == "ward nurse" for item in roles) == 1
        _labeled(app.button, "Continue").click().run()
        _labeled(app.multiselect, "Preferred countries").select("in").select("gb")
        _labeled(app.selectbox, "Remote preference").set_value("Hybrid")
        _labeled(app.text_input, "Add a location").set_value("Karnataka")
        _labeled(app.button, "Add location").click().run()
        _labeled(app.button, "Continue").click().run()
        assert "Profile summary" in _markdown(app)
        _labeled(app.button, "Save Changes").click().run()

    patches = [call[2] for call in calls if call[0] == "PATCH"]
    saved = patches[-1]
    assert len(patches) == 2
    assert saved["skills"] == ["Python", "Patient care"]
    assert saved["preferred_industries"] == ["it-jobs", "legal-jobs"]
    assert [item.casefold() for item in saved["preferred_roles"]] == ["data analyst", "ward nurse"]
    assert saved["preferred_countries"] == ["in", "gb"]
    assert saved["preferred_locations"] == ["London", "Karnataka"]
    assert saved["remote_preference"] == "hybrid"
    assert saved["education"] == "Mathematics"
