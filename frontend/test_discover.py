"""Discover Jobs uses a mocked catalog. No database writes."""

import json
import sys
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.job_filters import filter_jobs, search_from_params

from streamlit.testing.v1 import AppTest

FRONTEND_DIR = Path(__file__).resolve().parent
if str(FRONTEND_DIR) not in sys.path:
    sys.path.insert(0, str(FRONTEND_DIR))

from test_home_profile_saved import APP_PATH, _markdown

JOBS = [
    {
        "id": 7,
        "title": "Data Analyst",
        "company": "Northwind",
        "location": "Remote",
        "description": "Analyze the stored sales records for the operations team.",
        "required_skills": ["SQL", "Excel"],
        "min_experience": 2,
    },
    {
        "id": 8,
        "title": "Backend Engineer",
        "company": "Contoso",
        "location": "London",
        "description": "Build the API that serves the job catalog.",
        "required_skills": ["Python"],
        "min_experience": 0,
    },
]
SAVED = [
    {
        "id": 1,
        "created_at": "2026-11-21T09:00:00",
        "job": JOBS[0],
    }
]
MATCHES = [
    {
        "job": JOBS[0],
        "total_score": 82,
        "skill_score": 52,
        "role_score": 20,
        "location_score": 10,
    }
]


FILTERS = {
    "categories": [
        {"value": "it-jobs", "label": "IT Jobs"},
        {"value": "legal-jobs", "label": "Legal Jobs"},
    ],
    "countries": [
        {"value": "in", "label": "India"},
        {"value": "gb", "label": "United Kingdom"},
    ],
    "workplaces": [],
    "employment_types": [],
    "experience": [
        {"value": "any", "label": "Any"},
        {"value": "entry", "label": "Internship / entry-level"},
        {"value": "0-2", "label": "0–2 years"},
        {"value": "3-5", "label": "3–5 years"},
        {"value": "5plus", "label": "5+ years"},
        {"value": "unspecified", "label": "Experience not specified"},
    ],
    "salary_currencies": [],
    "sorts": [
        {"value": "newest", "label": "Newest first"},
        {"value": "match_score", "label": "Match score"},
    ],
    "category_status": "ready",
    "category_error": None,
}


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.status_code = status_code
        self.content = json.dumps(payload).encode()
        self._payload = payload

    def json(self):
        return self._payload


class _Journal:
    """In-memory preparation API. Each job id keeps its own tasks and notes."""

    def __init__(self, fixed=None):
        self.fixed = fixed
        self.plans = {}
        self.next_task = 100

    def response(self, method, url, payload):
        if self.fixed is not None and method == "GET":
            return FakeResponse(self.fixed)
        job_id = int(url.split("/jobs/")[1].split("/")[0])
        plan = self.plans.setdefault(
            job_id,
            {
                "id": job_id,
                "candidate_id": 4,
                "job_id": job_id,
                "notes": "",
                "next_action": "",
                "tasks": [
                    {
                        "id": job_id * 10 + 1,
                        "label": f"Read the complete job description for job {job_id}.",
                        "completed": False,
                        "is_custom": False,
                        "position": 0,
                    },
                    {
                        "id": job_id * 10 + 2,
                        "label": f"Review the required skills for job {job_id}.",
                        "completed": False,
                        "is_custom": False,
                        "position": 1,
                    },
                ],
            },
        )
        if method == "POST" and url.endswith("/tasks"):
            self.next_task += 1
            plan["tasks"].append(
                {
                    "id": self.next_task,
                    "label": payload["label"].strip(),
                    "completed": False,
                    "is_custom": True,
                    "position": len(plan["tasks"]),
                }
            )
            return FakeResponse(self._public(plan), 201)
        if method == "PATCH":
            task_id = int(url.rstrip("/").split("/")[-1])
            task = next(item for item in plan["tasks"] if item["id"] == task_id)
            task["completed"] = bool(payload["completed"])
            return FakeResponse(self._public(plan))
        if method == "DELETE":
            task_id = int(url.rstrip("/").split("/")[-1])
            task = next(item for item in plan["tasks"] if item["id"] == task_id)
            if not task["is_custom"]:
                return FakeResponse({"detail": "Only tasks you added can be deleted."}, 409)
            plan["tasks"] = [item for item in plan["tasks"] if item["id"] != task_id]
            return FakeResponse(self._public(plan))
        if method == "PUT":
            plan["notes"] = payload["notes"].strip()
            plan["next_action"] = payload["next_action"].strip()
            return FakeResponse(self._public(plan))
        return FakeResponse(self._public(plan))

    def _public(self, plan):
        tasks = list(plan["tasks"])
        completed = sum(1 for task in tasks if task["completed"])
        total = len(tasks)
        remaining = total - completed
        nxt = next(({"id": task["id"], "label": task["label"]} for task in tasks if not task["completed"]), None)
        body = dict(plan)
        body["tasks"] = tasks
        body["progress"] = {
            "completed": completed,
            "total": total,
            "remaining": remaining,
            "percent": 0 if total == 0 else (100 * completed + total // 2) // total,
            "finished": total > 0 and remaining == 0,
        }
        body["next_task"] = nxt
        return body


@contextmanager
def _discover(
    jobs=None,
    saved=None,
    matches=None,
    api_matches=None,
    jobs_status=200,
    jobs_error="",
    filters=None,
    filters_status=200,
    filters_error="",
    preparation_status=200,
    preparation_error="",
    preparation_plan=None,
    jooble_jobs=None,
    jooble_status=200,
    jooble_error="",
):
    calls = []
    catalog = JOBS if jobs is None else jobs
    library = SAVED if saved is None else saved
    journal = _Journal(preparation_plan)

    def fake_request(method, url, **kwargs):
        calls.append((method, url, kwargs.get("json")))
        parsed = urlparse(url)
        if method == "GET" and parsed.path.endswith("/jobs/jooble"):
            if jooble_jobs is None and jooble_status < 400:
                raise AssertionError(f"Unexpected API call {method} {url}")
            if jooble_status >= 400:
                return FakeResponse({"detail": jooble_error or "Jooble is unavailable."}, jooble_status)
            return FakeResponse({"jobs": jooble_jobs, "detail": None})
        if method == "GET" and parsed.path.endswith("/jobs/filters"):
            if filters_status >= 400:
                return FakeResponse({"detail": filters_error or "Categories are unavailable."}, filters_status)
            return FakeResponse(FILTERS if filters is None else filters)
        if method == "GET" and parsed.path.rstrip("/").endswith("/jobs"):
            if jobs_status >= 400:
                return FakeResponse({"detail": jobs_error or "The catalog is unavailable."}, jobs_status)
            query = {key: values[-1] for key, values in parse_qs(parsed.query).items()}
            return FakeResponse(filter_jobs(catalog, search_from_params(query)))
        if method == "GET" and url.endswith("/saved-jobs"):
            return FakeResponse(library)
        if method == "GET" and url.endswith("/matches"):
            return FakeResponse([] if api_matches is None else api_matches)
        if method == "POST" and url.endswith("/save"):
            return FakeResponse({"id": 9, "job_id": kwargs["json"]["candidate_id"], "job": JOBS[1], "created_at": "2026-11-21T12:00:00"})
        if "/preparation" in url:
            if preparation_status >= 400:
                return FakeResponse({"detail": preparation_error or "The preparation plan could not be read."}, preparation_status)
            return journal.response(method, url, kwargs.get("json") or {})
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
        app.session_state["nav"] = "Discover Jobs"
        app.session_state["auth_token"] = "test-token"
        app.session_state["candidate_id"] = 4
        app.session_state["candidate_name"] = "Ada Lovelace"
        app.session_state["profile"] = {"id": 4, "name": "Ada Lovelace", "email": "ada@example.com"}
        app.session_state["matches"] = matches
        app.run()
        assert not app.exception, app.exception
        yield app, calls


def test_discover_filters_details_score_and_save_use_the_catalog():
    with _discover(matches=MATCHES) as (app, calls):
        text = _markdown(app)
        assert "2 listings match." in text
        assert "Data Analyst" in text
        assert "Match 82" in text
        assert "Not ranked yet" in text
        assert any(button.label == "Saved" and button.disabled for button in app.button)
        assert not any(url.endswith("/matches") for _, url, _ in calls)

        app.text_input[0].set_value("Contoso").run()
        filtered = _markdown(app)
        assert "Backend Engineer" in filtered
        assert "Data Analyst" not in filtered

        app.text_input[0].set_value("").run()
        _keyed(app.text_input, "discover_location_text").set_value("London").run()
        located = _markdown(app)
        assert "Backend Engineer" in located
        assert "Data Analyst" not in located

        _keyed(app.text_input, "discover_location_text").set_value("").run()
        _labeled(app.selectbox, "Experience").set_value("entry").run()
        experienced = _markdown(app)
        assert "Backend Engineer" in experienced
        assert "Data Analyst" not in experienced

        _labeled(app.button, "Clear filters").click().run()
        cleared = _markdown(app)
        assert "Data Analyst" in cleared
        assert "Backend Engineer" in cleared

        _labeled(app.button, "View details").click().run()
        assert "Job details" in _markdown(app)
        assert "Build the API" in _markdown(app) or "Analyze the stored" in _markdown(app)

        next(button for button in app.button if button.key == "save-8").click().run()
        assert any("Saved Backend Engineer." in item.value for item in app.success)
        assert any(method == "POST" and url.endswith("/jobs/8/save") for method, url, _ in calls)


def test_discover_empty_catalog_and_failed_request():
    with _discover(jobs=[], saved=[]) as (app, calls):
        assert "No jobs are stored yet" in _markdown(app)
        assert "Data Analyst" not in _markdown(app)
        assert not any(method == "POST" for method, _, _ in calls)

    with _discover(jobs_status=500, jobs_error="The catalog is unavailable.") as (app, _calls):
        assert any("The catalog is unavailable." in item.value for item in app.error)
        assert "Data Analyst" not in _markdown(app)


def test_job_cards_keep_a_short_square_layout():
    from theme import CSS

    assert "repeat(3, minmax(0, 1fr))" in CSS
    assert "@media (max-width: 1100px)" in CSS
    assert "repeat(2, minmax(0, 1fr))" in CSS
    assert "@media (max-width: 680px)" in CSS
    assert "grid-template-columns: minmax(0, 1fr)" in CSS
    assert "@media (max-width: 390px)" in CSS
    source = Path(__file__).resolve().parents[0].joinpath("pages.py").read_text(encoding="utf-8")
    assert "st.columns(len(jobs)" not in source
    assert "st.columns(3, gap=\"medium\")" in source
    long_title = "Principal Applied Machine Learning Engineer for Customer Platforms and Research"
    long_job = {
        "id": 9,
        "title": long_title,
        "company": "Northwind Analytics Group International",
        "location": "Remote",
        "description": "A long description that belongs in the details, not on the card.",
        "required_skills": ["SQL", "Excel", "Python", "Tableau", "Statistics"],
        "min_experience": 4,
    }
    with _discover(jobs=[long_job], saved=[], matches=None) as (app, calls):
        text = _markdown(app)
        assert "<h3 class='match-title discover-card'>" in text
        assert long_title not in text
        assert "…" in text
        assert "+2 more in details" in text
        assert "A long description" not in text
        assert "Not ranked yet" in text
        assert "Minimum experience: 4 years" in text
        assert not any("/preparation" in url for _, url, _ in calls)
        assert sum(url.endswith("/matches") for _, url, _ in calls) == 1

        next(button for button in app.button if button.key == "detail-9").click().run()
        opened = _markdown(app)
        assert f"<h3 class='match-title job-detail'>{long_title}</h3>" in opened
        assert "A long description" in opened
        assert "Tableau" in opened
        assert sum("/jobs/9/preparation" in url and method == "GET" for method, url, _ in calls) == 1


def test_twenty_one_listings_each_get_a_card_and_search_still_filters():
    catalog = [
        {
            "id": index,
            "title": f"Role {index}",
            "company": "Northwind",
            "location": "Remote" if index % 2 else "London",
            "description": f"Description for role {index}.",
            "required_skills": ["SQL", "Excel"],
            "min_experience": index % 3,
        }
        for index in range(1, 22)
    ]
    with _discover(jobs=catalog, saved=[], matches=None) as (app, calls):
        text = _markdown(app)
        assert text.count("<h3 class='match-title discover-card'>") == 21
        assert "21 listings match." in text
        assert sum(button.label == "View details" for button in app.button) == 21
        assert sum(button.label == "Save Job" for button in app.button) == 21
        assert not any("/preparation" in url for _, url, _ in calls)

        app.text_input[0].set_value("Role 21").run()
        filtered = _markdown(app)
        assert filtered.count("<h3 class='match-title discover-card'>") == 1
        assert "<h3 class='match-title discover-card'>Role 21</h3>" in filtered
        assert "<h3 class='match-title discover-card'>Role 2</h3>" not in filtered


def test_preparation_journal_is_saved_per_job():
    with _discover(matches=MATCHES) as (app, calls):
        next(button for button in app.button if button.key == "detail-7").click().run()
        opened = _markdown(app)
        assert "My Preparation Plan" in opened
        assert "What's Next?" in opened
        assert "0 / 2 tasks" in opened
        assert any(box.label == "Read the complete job description for job 7." for box in app.checkbox)
        assert not any("for job 8." in box.label for box in app.checkbox)

        _keyed(app.text_input, "prep-new-7").set_value("Practice a SQL case study").run()
        next(button for button in app.button if button.key == "prep-add-7").click().run()
        assert any(box.label == "Practice a SQL case study" for box in app.checkbox)
        assert "0 / 3 tasks" in _markdown(app)

        _keyed(app.checkbox, "prep-task-71").set_value(True).run()
        checked = _markdown(app)
        assert "1 / 3 tasks" in checked
        assert "1 completed · 2 remaining" in checked

        _keyed(app.checkbox, "prep-task-71").set_value(False).run()
        assert "0 / 3 tasks" in _markdown(app)

        next(button for button in app.button if button.key == "prep-delete-101").click().run()
        assert not any(box.label == "Practice a SQL case study" for box in app.checkbox)
        assert "0 / 2 tasks" in _markdown(app)

        _keyed(app.text_area, "prep-notes-7").set_value("Review the SQL examples.").run()
        _keyed(app.text_input, "prep-action-7").set_value("Rewrite the project summary.").run()
        next(button for button in app.button if button.key == "prep-save-7").click().run()
        assert any("Notes saved for this job." in item.value for item in app.success)
        assert _keyed(app.text_area, "prep-notes-7").value == "Review the SQL examples."
        assert _keyed(app.text_input, "prep-action-7").value == "Rewrite the project summary."

        next(button for button in app.button if button.key == "detail-8").click().run()
        assert any(box.label == "Read the complete job description for job 8." for box in app.checkbox)
        assert _keyed(app.text_area, "prep-notes-8").value == ""
        assert sum(method == "GET" and url.endswith("/jobs/7/preparation") for method, url, _ in calls) == 1
        assert sum(method == "GET" and url.endswith("/jobs/8/preparation") for method, url, _ in calls) == 1


def test_preparation_empty_and_failed_states_do_not_invent_tasks():
    empty_plan = {
        "id": 1,
        "candidate_id": 4,
        "job_id": 7,
        "notes": "",
        "next_action": "",
        "tasks": [],
        "progress": {"completed": 0, "total": 0, "remaining": 0, "percent": 0, "finished": False},
        "next_task": None,
    }
    with _discover(preparation_plan=empty_plan) as (app, _calls):
        next(button for button in app.button if button.key == "detail-7").click().run()
        text = _markdown(app)
        assert "No preparation tasks yet" in text
        assert "0 / 0 tasks" in text
        assert "All preparation tasks for this job are complete." not in text
        assert "Read the complete job description" not in text

    with _discover(
        preparation_status=403,
        preparation_error="You cannot open another candidate's profile.",
    ) as (app, _calls):
        next(button for button in app.button if button.key == "detail-7").click().run()
        assert any(
            "You cannot open another candidate's profile." in item.value for item in app.error
        )
        assert "Read the complete job description" not in _markdown(app)

    with _discover(preparation_status=401, preparation_error="Log in to continue.") as (app, _calls):
        next(button for button in app.button if button.key == "detail-7").click().run()
        assert "<p class='section-label auth-card'>Sign in</p>" in _markdown(app)


def test_discover_loads_cached_scores_from_the_matching_service():
    with _discover(matches=None, api_matches=MATCHES) as (app, calls):
        text = _markdown(app)
        assert "Match 82" in text
        assert "Not ranked yet" in text
        assert sum(url.endswith("/matches") for _, url, _ in calls) == 1


def test_external_listing_stays_visible_without_a_match_score():
    external = {
        "id": 90,
        "title": "Python Developer",
        "company": "Northwind Listings",
        "location": "London",
        "description": "A short provider snippet.",
        "required_skills": [],
        "min_experience": 0,
        "source": "adzuna",
        "source_country": "in",
        "source_url": "https://www.adzuna.in/details/90",
        "posted_at": "2026-11-22T06:39:21+00:00",
        "is_matchable": False,
        "requirements_available": False,
        "matchability_status": "unmatchable",
        "description_is_snippet": True,
    }
    with _discover(jobs=[*JOBS, external], saved=[], matches=MATCHES) as (app, calls):
        text = _markdown(app)
        assert "Python Developer" in text
        assert "Match score unavailable" in text
        assert "This listing does not provide enough verified skill requirements for reliable matching." in text
        assert "Not ranked yet" in text
        assert "Skills not provided by source" in text
        assert "Experience requirement not specified" in text
        assert "Salary not provided" in text
        assert "Work arrangement not specified" in text
        assert "Source: Adzuna" in text
        assert "Country: India" in text
        assert "Posted: 2026-11-22 06:39" in text
        assert "None" not in text
        assert not any(getattr(item, "value", None) == "None" for item in app.caption)
        assert "https://www.adzuna.in/" in text
        assert "adzuna-credit" in text
        assert ">Adzuna</a>" in text
        assert "https://www.adzuna.in/details/90" in text
        assert "View original listing" in text
        assert "Match 82" in text
        assert any(button.label == "Save Job" and button.key == "save-90" for button in app.button)

        next(button for button in app.button if button.key == "save-90").click().run()
        assert not app.exception, app.exception
        assert ("POST", "http://127.0.0.1:8001/jobs/90/save", {"candidate_id": 4}) in calls

        next(button for button in app.button if button.key == "detail-90").click().run()
        detail = _markdown(app)
        assert "provider supplied a description snippet" in detail
        assert "Match score unavailable" in detail
        theme = Path(__file__).resolve().parent.joinpath("theme.py").read_text(encoding="utf-8")
        assert "min-width: 116px" in theme
        assert "min-height: 23px" in theme


def test_discover_filters_use_provider_categories_and_cache_them():
    catalogue = {
        **FILTERS,
        "workplaces": [{"value": "remote", "label": "Remote"}, {"value": "hybrid", "label": "Hybrid"}, {"value": "onsite", "label": "Onsite"}],
        "employment_types": [{"value": "full_time", "label": "Full-time"}, {"value": "internship", "label": "Internship"}],
        "salary_currencies": ["GBP", "INR"],
    }
    jobs = [
        {
            "id": 1,
            "title": "Python Developer",
            "company": "Northwind",
            "location": "Bengaluru, Karnataka",
            "required_skills": ["Python"],
            "min_experience": 4,
            "source_country": "in",
            "category_label": "IT Jobs",
            "category_tag": "it-jobs",
            "workplace": "remote",
            "contract_time": "full_time",
            "salary_min": 900000,
            "salary_currency": "INR",
            "posted_at": "2026-11-21T00:00:00Z",
        },
        {
            "id": 2,
            "title": "Solicitor",
            "company": "Harbor",
            "location": "Manchester",
            "required_skills": ["Contracts"],
            "min_experience": 0,
            "source_country": "gb",
            "category_label": "Legal Jobs",
            "category_tag": "legal-jobs",
            "workplace": "onsite",
            "contract_type": "permanent",
            "salary_min": 40000,
            "salary_currency": "GBP",
            "posted_at": "2026-11-22T00:00:00Z",
            "is_matchable": False,
            "requirements_available": False,
        },
        {
            "id": 3,
            "title": "Intern Analyst",
            "company": "Northwind",
            "location": "Pune",
            "required_skills": ["Excel"],
            "min_experience": 0,
            "source_country": "in",
            "workplace": "hybrid",
            "contract_time": "internship",
            "posted_at": "2026-11-20T00:00:00Z",
        },
    ]
    with _discover(jobs=jobs, saved=[], matches=MATCHES, filters=catalogue) as (app, calls):
        text = _markdown(app)
        assert "Industry: IT Jobs" in text
        assert "Industry: Legal Jobs" in text
        assert "Other / Not specified" in text
        assert "Industry categories could not be loaded" not in text
        assert sum(url.endswith("/jobs/filters") for _, url, _ in calls) == 1

        _labeled(app.selectbox, "Industry").set_value("legal-jobs").run()
        legal = _markdown(app)
        assert "Solicitor" in legal
        assert "Python Developer" not in legal
        assert sum(url.endswith("/jobs/filters") for _, url, _ in calls) == 1

        _labeled(app.selectbox, "Industry").set_value("unspecified").run()
        unspecified = _markdown(app)
        assert "Intern Analyst" in unspecified
        assert "Solicitor" not in unspecified
        assert "Other / Not specified" in unspecified

        _labeled(app.selectbox, "Industry").set_value("all").run()
        _labeled(app.selectbox, "Country").set_value("gb").run()
        _keyed(app.text_input, "discover_location_text").set_value("man").run()
        combined = _markdown(app)
        assert "Solicitor" in combined
        assert "Python Developer" not in combined
        assert "Intern Analyst" not in combined

        _labeled(app.selectbox, "Country").set_value("worldwide").run()
        _keyed(app.text_input, "discover_location_text").set_value("").run()
        _labeled(app.selectbox, "Work arrangement").set_value("remote").run()
        remote = _markdown(app)
        assert "Python Developer" in remote
        assert "Work arrangement: Remote" in remote
        assert "Solicitor" not in remote

        _labeled(app.selectbox, "Work arrangement").set_value("any").run()
        _labeled(app.selectbox, "Employment type").set_value("internship").run()
        intern = _markdown(app)
        assert "Intern Analyst" in intern
        assert "Employment type: Internship" in intern
        assert "Python Developer" not in intern

        _labeled(app.selectbox, "Employment type").set_value("any").run()
        _labeled(app.selectbox, "Experience").set_value("3-5").run()
        experienced = _markdown(app)
        assert "Python Developer" in experienced
        assert "Intern Analyst" not in experienced
        assert "Solicitor" not in experienced

        _labeled(app.selectbox, "Experience").set_value("unspecified").run()
        unknown = _markdown(app)
        assert "Solicitor" in unknown
        assert "Experience requirement not specified" in unknown
        assert "Python Developer" not in unknown

        _labeled(app.selectbox, "Experience").set_value("any").run()
        _labeled(app.selectbox, "Salary currency").set_value("GBP").run()
        _keyed(app.text_input, "discover_salary_min").set_value("30000").run()
        paid = _markdown(app)
        assert "Solicitor" in paid
        assert "Salary: 40000 GBP" in paid
        assert "Python Developer" not in paid
        assert "INR" not in paid or "900000" not in paid

        _labeled(app.selectbox, "Salary currency").set_value("any").run()
        _labeled(app.selectbox, "Sort").set_value("match_score").run()
        ranked = _markdown(app)
        assert ranked.find("Python Developer") < ranked.find("Solicitor")
        assert "Match score unavailable" in ranked
        assert sum(url.endswith("/jobs/filters") for _, url, _ in calls) == 1


def test_jooble_live_results_stay_beside_the_catalog():
    live = [
        {
            "id": "jooble-in-platform",
            "title": "Platform Engineer",
            "company": "",
            "location": "Bengaluru",
            "description": "Build the listing services for the marketplace.",
            "required_skills": [],
            "source": "jooble",
            "publisher": "Example Board",
            "source_country": "in",
            "source_url": "https://in.jooble.org/jdp/501",
            "posted_at": "2026-11-22T08:00:00",
            "is_matchable": False,
            "requirements_available": False,
            "description_is_snippet": True,
            "salary_min": 900000,
            "salary_currency": "INR",
            "contract_time": "full_time",
        },
        {
            "id": "jooble-in-copy",
            "title": "Backend Engineer",
            "company": "Contoso",
            "location": "Bengaluru",
            "description": "Duplicate of a stored listing.",
            "source": "jooble",
            "source_country": "gb",
            "source_url": "https://example.com/copy",
        },
    ]
    catalog = [
        {
            "id": 8,
            "title": "Backend Engineer",
            "company": "Contoso",
            "location": "Bengaluru",
            "description": "Build the API that serves the job catalog.",
            "required_skills": ["Python"],
            "min_experience": 0,
            "source": "adzuna",
            "source_country": "in",
        }
    ]
    with _discover(jobs=catalog, saved=[], matches=MATCHES, jooble_jobs=live) as (app, calls):
        _labeled(app.selectbox, "Country").set_value("in").run()
        _labeled(app.text_input, "Search jobs").set_value("Engineer").run()
        text = _markdown(app)
        jooble_calls = [url for _, url, _ in calls if "/jobs/jooble" in url]
        assert len(jooble_calls) == 1
        assert "country=in" in jooble_calls[0]
        assert "q=Engineer" in jooble_calls[0]
        assert "country=gb" not in jooble_calls[0]
        assert "Platform Engineer" in text
        assert "Company not provided" in text
        assert "Source: Jooble" in text
        assert "Publisher: Example Board" in text
        assert "Salary: 900000 INR" in text
        assert "https://in.jooble.org/" in text
        assert "Match score unavailable" in text
        assert any("Live results are not stored." in item.value for item in app.caption)
        assert text.count("Backend Engineer") == 1
        assert "Data Analyst" not in text

    with _discover(jobs=catalog, saved=[], matches=MATCHES, jooble_status=503, jooble_error="Jooble did not respond in time.") as (app, _calls):
        _labeled(app.selectbox, "Country").set_value("in").run()
        _labeled(app.text_input, "Search jobs").set_value("Engineer").run()
        assert any("Jooble did not respond in time." in item.value for item in app.warning)
        assert "Backend Engineer" in _markdown(app)


def test_empty_industry_is_not_reported_as_an_api_error():
    with _discover(jobs=JOBS, saved=[], matches=None) as (app, _calls):
        _labeled(app.selectbox, "Industry").set_value("legal-jobs").run()
        assert any("No listings match these filters" in item.value for item in app.markdown)
        assert not app.error

    with _discover(jobs_status=503, jobs_error="The catalog is unavailable.") as (app, _calls):
        assert any("The catalog is unavailable." in item.value for item in app.error)
        assert not any("No listings match these filters" in item.value for item in app.markdown)


def test_category_metadata_failure_is_separate_from_an_empty_search():
    with _discover(filters_status=503, filters_error="Categories are unavailable.") as (app, calls):
        text = _markdown(app)
        assert any("Categories are unavailable." in item.value for item in app.warning)
        assert "Data Analyst" in text
        assert "Other / Not specified" in text
        assert sum(url.endswith("/jobs/filters") for _, url, _ in calls) == 1


def _labeled(widgets, label):
    return next(widget for widget in widgets if widget.label == label)


def _keyed(widgets, key):
    return next(widget for widget in widgets if widget.key == key)
