"""Sample-data checks for Home, My Profile, and Saved Jobs. No live API calls."""

from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parent / "app.py"

SAVED_JOBS = [
    {
        "id": 1,
        "created_at": "2026-11-20T10:00:00",
        "job": {
            "id": 3,
            "title": "Zebra Role",
            "company": "Northwind",
            "location": "Remote",
            "description": "Analyze data.",
            "required_skills": ["SQL"],
            "min_experience": 2,
        },
    },
    {
        "id": 2,
        "created_at": "2026-11-21T09:00:00",
        "job": {
            "id": 4,
            "title": "Alpha Role",
            "company": "Contoso",
            "location": "London",
            "description": "Build interfaces.",
            "required_skills": ["Python"],
            "min_experience": 0,
        },
    },
]


class FakeResponse:
    """Stand-in for requests.Response, including the body attribute the client reads."""

    def __init__(self, payload):
        self.status_code = 200
        self.text = ""
        self.content = b"{}"
        self._payload = payload

    def json(self):
        return self._payload


@contextmanager
def _mocked_app(page: str, **state):
    """Keep the API mock active for the whole test, including later button clicks."""
    calls = []
    created = {}

    def fake_request(method, url, **kwargs):
        calls.append((method, url, kwargs.get("json")))
        if method == "PATCH" and url.endswith("/candidates/4"):
            body = kwargs["json"]
            created["profile"] = {
                "id": 4,
                "name": body["name"],
                "email": body["email"],
                "education": body["education"],
                "skills": body["skills"],
                "preferred_roles": body["preferred_roles"],
                "preferred_locations": body["preferred_locations"],
                "years_experience": body["years_experience"],
            }
            return FakeResponse(created["profile"])
        if method == "GET" and url.endswith("/candidates/4"):
            return FakeResponse(created["profile"])
        if method == "GET" and url.endswith("/saved-jobs"):
            return FakeResponse(SAVED_JOBS)
        if method == "GET" and url.endswith("/jobs/filters"):
            return FakeResponse(
                {
                    "categories": [],
                    "countries": [],
                    "workplaces": [],
                    "employment_types": [],
                    "experience": [{"value": "any", "label": "Any"}],
                    "salary_currencies": [],
                    "sorts": [{"value": "newest", "label": "Newest first"}],
                    "category_status": "ready",
                }
            )
        if method == "GET" and (url.split("?")[0].endswith("/jobs/") or url.endswith("/matches")):
            return FakeResponse([])
        if method != "GET" or not url.endswith(":8001/"):
            raise AssertionError(f"Unexpected API call {method} {url}")
        return FakeResponse({"status": "ok", "message": "API is running."})

    def reject_session_request(*args, **kwargs):
        raise AssertionError("Session.request was called; the mock did not intercept it.")

    with (
        patch("requests.request", fake_request),
        patch("requests.sessions.Session.request", reject_session_request),
    ):
        app = AppTest.from_file(str(APP_PATH))
        app.session_state["nav"] = page
        for key, value in state.items():
            app.session_state[key] = value
        app.run()
        assert not app.exception, app.exception
        yield app, calls


def _markdown(app) -> str:
    return "\n".join(item.value for item in app.markdown)


def test_signed_out_home_opens_login_and_signed_in_home_loads_the_dashboard():
    """A signed-out visit opens Login. A signed-in Home loads the candidate's own figures once."""
    with _mocked_app("Home") as (empty, empty_calls):
        empty_markdown = _markdown(empty)
        assert "<p class='section-label auth-card'>Sign in</p>" in empty_markdown
        assert "The local API is not reachable." not in empty_markdown
        assert "API is running." in empty_markdown
        assert _labeled(empty.text_input, "Email").label == "Email"
        assert _labeled(empty.text_input, "Password").label == "Password"
        assert empty_calls == [("GET", "http://127.0.0.1:8001/", None)]

    profile = {
        "id": 4,
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "education": "Mathematics",
        "skills": ["Python", "SQL"],
        "preferred_roles": ["Analyst"],
        "preferred_locations": ["London"],
        "years_experience": 3,
    }
    with _mocked_app(
        "Home",
        auth_token="test-token",
        candidate_id=4,
        candidate_name="Ada Lovelace",
        profile=profile,
        matches=None,
        saved_jobs=None,
    ) as (home, calls):
        text = _markdown(home)
        assert "Hello, Ada Lovelace" in " ".join(item.value for item in home.title)
        assert "<p class='section-label kpi-card'>Total jobs</p>" in text
        assert "<p class='section-label home-saved home-panel'>Recently saved jobs</p>" in text
        assert "Zebra Role" in text
        assert any(url.endswith("/matches") for _, url, _ in calls)
        assert any(url.endswith("/jobs/") for _, url, _ in calls)
        assert sum(url.endswith("/matches") for _, url, _ in calls) == 1


def _labeled(widgets, label):
    return next(widget for widget in widgets if widget.label == label)


def test_profile_form_keeps_the_create_payload():
    """Saving a profile sends the existing fields and then reads that profile back."""
    with _mocked_app("My Profile", auth_token="test-token", candidate_id=4) as (app, calls):
        text = _markdown(app)
        assert "<p class='section-label profile-card profile-builder'>Education and background</p>" in text
        assert "1. Education" in text

        _labeled(app.text_input, "Name").set_value("Ada Lovelace")
        _labeled(app.text_input, "Email").set_value("Ada@Example.com")
        _labeled(app.selectbox, "Education").set_value("B.Tech")
        _labeled(app.selectbox, "Years of experience").set_value(3)
        _labeled(app.button, "Continue").click().run()
        _labeled(app.multiselect, "Skills").select("Python").select("SQL")
        _labeled(app.button, "Continue").click().run()
        _labeled(app.multiselect, "Preferred roles").select("Data Analyst")
        _labeled(app.button, "Continue").click().run()
        _labeled(app.multiselect, "Preferred locations").select("Bengaluru")
        _labeled(app.button, "Save Changes").click().run()

        assert not app.exception, app.exception
        posts = [call for call in calls if call[0] == "PATCH"]
        assert posts == [
            (
                "PATCH",
                "http://127.0.0.1:8001/candidates/4",
                {
                    "name": "Ada Lovelace",
                    "email": "ada@example.com",
                    "education": "B.Tech",
                    "degree": None,
                    "field_of_study": None,
                    "specialization": None,
                    "institution": None,
                    "graduation_year": None,
                    "skills": ["Python", "SQL"],
                    "preferred_roles": ["Data Analyst"],
                    "preferred_industries": [],
                    "preferred_locations": ["Bengaluru"],
                    "preferred_countries": [],
                    "remote_preference": None,
                    "years_experience": 3,
                },
            )
        ]
        assert ("GET", "http://127.0.0.1:8001/candidates/4", None) in calls
        assert [item.value for item in app.success] == [
            "Profile saved. Your candidate id is 4. Open Match Insights next."
        ]
        summary = _markdown(app)
        assert "<p class='section-label profile-overview'>Candidate Profile</p>" in summary
        assert "<p class='profile-percent'>100%</p>" in summary
        assert "Ada Lovelace" in summary
        assert '<span class="chip chip-exact">SQL</span>' in summary
        assert all(method != "POST" or url.endswith("/candidates/") for method, url, _ in calls)


def test_profile_custom_entries_and_validation_stay_mocked():
    """Custom education and skills are sent as plain text. Invalid input makes no request."""
    with _mocked_app("My Profile", auth_token="test-token", candidate_id=4) as (app, calls):
        _labeled(app.button, "Continue").click().run()
        _labeled(app.text_input, "Add a skill").set_value("  Fortran  ")
        _labeled(app.button, "Add skill").click().run()
        assert not app.exception, app.exception
        assert "Fortran" in _labeled(app.multiselect, "Skills").value
        assert not any(method == "POST" for method, _, _ in calls)

        _labeled(app.text_input, "Add a skill").set_value("fortran")
        _labeled(app.button, "Add skill").click().run()
        assert _labeled(app.multiselect, "Skills").value.count("Fortran") == 1

        _labeled(app.text_input, "Add a skill").set_value("   ")
        _labeled(app.button, "Add skill").click().run()
        assert any("Enter a skill to add." in item.value for item in app.warning)
        assert "Fortran" in _labeled(app.multiselect, "Skills").value

        _labeled(app.button, "Back").click().run()
        _labeled(app.text_input, "Name").set_value("Ada Lovelace")
        _labeled(app.text_input, "Email").set_value("not-an-email")
        _labeled(app.button, "Save Changes").click().run()
        assert any("email" in item.value.casefold() for item in app.error)
        assert not any(method == "POST" for method, _, _ in calls)

        _labeled(app.text_input, "Email").set_value("ada@example.com")
        _labeled(app.selectbox, "Education").set_value("Other").run()
        _labeled(app.text_input, "Custom education").set_value("B.A. Mathematics")
        _labeled(app.selectbox, "Years of experience").set_value(1)
        _labeled(app.button, "Continue").click().run()
        _labeled(app.button, "Continue").click().run()
        _labeled(app.multiselect, "Preferred roles").select("Data Analyst")
        _labeled(app.button, "Continue").click().run()
        _labeled(app.multiselect, "Preferred locations").select("Remote")
        _labeled(app.button, "Save Changes").click().run()

        assert not app.exception, app.exception
        assert not list(app.error), [item.value for item in app.error]
        posts = [call for call in calls if call[0] == "PATCH"]
        assert len(posts) == 1
        body = posts[0][2]
        assert body["education"] == "B.A. Mathematics"
        assert body["skills"] == ["Fortran"]
        assert body["preferred_roles"] == ["Data Analyst"]
        assert body["preferred_locations"] == ["Remote"]
        assert body["years_experience"] == 1
        assert posts[0][1] == "http://127.0.0.1:8001/candidates/4"
        saved = _markdown(app)
        assert "B.A. Mathematics" in saved
        assert '<span class="chip chip-exact">Fortran</span>' in saved
        assert "Categories and proficiency levels are not stored" in saved
        assert "Beginner" not in saved


def test_saved_jobs_cards_search_and_sort_stay_mocked():
    """Saved jobs render from the mocked list and never send a write."""
    with _mocked_app(
        "Saved Jobs",
        auth_token="test-token",
        candidate_id=1,
        candidate_name="Ada Lovelace",
        saved_jobs=None,
    ) as (app, calls):
        text = _markdown(app)
        assert text.index("Zebra Role") < text.index("Alpha Role")
        assert "<h3 class='match-title saved-card discover-card'>Zebra Role</h3>" in text
        assert "<div class='insight-panel'>Analyze data.</div>" in text
        assert "Saved 2026-11-20 10:00" in text
        assert '<span class="chip chip-exact">SQL</span>' in text
        assert "Minimum experience: 2 years" in text
        assert "Unsave" not in " ".join(button.label for button in app.button)
        assert ("GET", "http://127.0.0.1:8001/candidates/1/saved-jobs", None) in calls
        assert not any(method == "POST" for method, _, _ in calls)

        app.selectbox[0].set_value("Title").run()
        assert not app.exception, app.exception
        sorted_text = _markdown(app)
        assert sorted_text.index("Alpha Role") < sorted_text.index("Zebra Role")

        app.text_input[0].set_value("Northwind").run()
        assert not app.exception, app.exception
        filtered = _markdown(app)
        assert "Zebra Role" in filtered
        assert "Alpha Role" not in filtered
        assert not any(method == "POST" for method, _, _ in calls)
        assert sum(url.endswith("/saved-jobs") for _, url, _ in calls) == 1


def test_saved_jobs_use_three_card_rows_and_open_the_same_details():
    """Four saved jobs stay in batches of three. Scores and details come from real payloads."""
    import json
    from unittest.mock import patch

    long_description = "A " + ("detailed responsibility " * 20)
    catalog = []
    for index in range(1, 5):
        catalog.append(
            {
                "id": index,
                "created_at": f"2026-11-2{index}T08:00:00",
                "job": {
                    "id": 10 + index,
                    "title": "Principal Applied Machine Learning Engineer for Customer Platforms" if index == 1 else f"Role {index}",
                    "company": "Northwind",
                    "location": "Remote",
                    "description": long_description if index == 1 else f"Short description {index}.",
                    "required_skills": ["SQL", "Excel", "Python", "Tableau", "Statistics"] if index == 1 else ["SQL"],
                    "min_experience": 2,
                },
            }
        )

    class Response:
        def __init__(self, payload, status_code=200):
            self.status_code = status_code
            self.content = json.dumps(payload).encode()
            self._payload = payload

        def json(self):
            return self._payload

    calls = []

    def fake_request(method, url, **kwargs):
        calls.append((method, url, kwargs.get("json")))
        if method == "GET" and url.endswith("/saved-jobs"):
            return Response(catalog)
        if method == "GET" and "/preparation" in url:
            return Response(
                {
                    "id": 1,
                    "candidate_id": 1,
                    "job_id": 11,
                    "notes": "",
                    "next_action": "",
                    "tasks": [
                        {
                            "id": 5,
                            "label": "Read the complete job description for this saved role.",
                            "completed": False,
                            "is_custom": False,
                            "position": 0,
                        }
                    ],
                    "progress": {"completed": 0, "total": 1, "remaining": 1, "percent": 0, "finished": False},
                    "next_task": {"id": 5, "label": "Read the complete job description for this saved role."},
                }
            )
        if method == "GET" and url.endswith(":8001/"):
            return Response({"status": "ok", "message": "API is running."})
        raise AssertionError(f"Unexpected API call {method} {url}")

    source = Path(__file__).resolve().parent.joinpath("pages.py").read_text(encoding="utf-8")
    assert "for start in range(0, len(items), 3)" in source
    assert "st.columns(len(items)" not in source
    assert "repeat(3, minmax(0, 1fr))" in Path(__file__).resolve().parent.joinpath("theme.py").read_text(encoding="utf-8")
    assert "repeat(2, minmax(0, 1fr))" in Path(__file__).resolve().parent.joinpath("theme.py").read_text(encoding="utf-8")
    assert "grid-template-columns: minmax(0, 1fr)" in Path(__file__).resolve().parent.joinpath("theme.py").read_text(encoding="utf-8")

    with (
        patch("requests.request", fake_request),
        patch("requests.sessions.Session.request", side_effect=AssertionError("bypass")),
    ):
        app = AppTest.from_file(str(APP_PATH))
        app.session_state["nav"] = "Saved Jobs"
        app.session_state["auth_token"] = "test-token"
        app.session_state["candidate_id"] = 1
        app.session_state["candidate_name"] = "Ada Lovelace"
        app.session_state["saved_jobs"] = None
        app.session_state["matches"] = [
            {"job": catalog[0]["job"], "total_score": 82},
        ]
        app.run()
        assert not app.exception, app.exception
        text = _markdown(app)
        assert text.count("<h3 class='match-title saved-card discover-card'>") == 4
        assert "Match 82" in text
        assert text.count("Not ranked yet") == 3
        assert "+2 more in details" in text
        assert "Tableau" not in text.split("Job details")[0]
        assert long_description not in text
        assert "…" in text
        assert "Saved 2026-11-21 08:00" in text
        assert "Unsave" not in " ".join(button.label for button in app.button)

        next(button for button in app.button if button.key == "saved-detail-1").click().run()
        opened = _markdown(app)
        assert "Job details" in opened
        assert long_description in opened
        assert "Tableau" in opened
        assert "My Preparation Plan" in opened
        assert sum("/preparation" in url for _, url, _ in calls) == 1
