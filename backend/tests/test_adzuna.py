"""Checks for the Adzuna client. These tests never call the live API."""

import sys
import traceback
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.adzuna import (
    AdzunaAuthError,
    AdzunaCredentialsError,
    AdzunaError,
    AdzunaRateLimitError,
    AdzunaTimeoutError,
    list_categories,
    search_jobs,
)


SECRET = "adzuna-secret-value"
APP_ID = "test-app-id"


class FakeResponse:
    def __init__(self, status_code=200, payload=None, json_error=None, text=""):
        self.status_code = status_code
        self.payload = payload
        self.json_error = json_error
        self.text = text
        self.url = f"https://api.adzuna.com/v1/api/jobs/gb/search/1?app_key={SECRET}"

    def json(self):
        if self.json_error is not None:
            raise self.json_error
        return self.payload


class FakeSession:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params, timeout))
        if self.error is not None:
            raise self.error
        return self.response


def listing(**overrides):
    row = {
        "title": "Python Developer",
        "company": {"display_name": "Northwind"},
        "location": {"display_name": "London"},
        "id": 5961663420,
        "description": "Write Python services and review API changes.",
        "created": "2026-11-21T09:00:00Z",
        "redirect_url": "https://www.adzuna.co.uk/jobs/example",
    }
    row.update(overrides)
    return row


class AdzunaClientTests(unittest.TestCase):
    def test_successful_response_returns_only_safe_listing_fields(self):
        session = FakeSession(
            FakeResponse(
                payload={
                    "count": 40,
                    "results": [
                        listing(),
                        listing(title="Backend Engineer", company={"display_name": "Contoso"}),
                    ],
                }
            )
        )
        with self._credentials():
            result = search_jobs(what="Python Developer", results_per_page=5, session=session)

        self.assertEqual(result.status_code, 200)
        self.assertEqual(len(result.jobs), 2)
        self.assertEqual(result.jobs[0].title, "Python Developer")
        self.assertEqual(result.jobs[0].company, "Northwind")
        self.assertEqual(result.jobs[0].location, "London")
        self.assertEqual(result.jobs[0].created, "2026-11-21T09:00:00Z")
        self.assertEqual(result.jobs[0].redirect_url, "https://www.adzuna.co.uk/jobs/example")
        self.assertEqual(result.jobs[0].external_id, "5961663420")
        self.assertEqual(result.jobs[0].description, "Write Python services and review API changes.")
        self.assertNotIn(SECRET, result.jobs[0].redirect_url)

    def test_listing_link_drops_a_query_value_that_repeats_the_application_id(self):
        session = FakeSession(
            FakeResponse(
                payload={
                    "results": [
                        listing(
                            redirect_url=(
                                "https://www.adzuna.co.uk/jobs/land/ad/123"
                                f"?utm_medium=api&utm_source={SECRET}&se=public-token"
                            )
                        )
                    ]
                }
            )
        )
        with self._credentials():
            result = search_jobs(what="Python Developer", session=session)

        self.assertEqual(
            result.jobs[0].redirect_url,
            "https://www.adzuna.co.uk/jobs/land/ad/123?utm_medium=api&se=public-token",
        )
        self.assertNotIn(SECRET, result.jobs[0].redirect_url)
        url, params, timeout = session.calls[0]
        self.assertEqual(url, "https://api.adzuna.com/v1/api/jobs/gb/search/1")
        self.assertEqual(params["app_id"], APP_ID)
        self.assertEqual(params["app_key"], SECRET)
        self.assertEqual(params["results_per_page"], 5)
        self.assertEqual(params["what"], "Python Developer")
        self.assertEqual(params["content-type"], "application/json")
        self.assertEqual(timeout, 15)
        self.assertNotIn(SECRET, url)

    def test_missing_credentials_do_not_call_the_api(self):
        session = FakeSession(FakeResponse(payload={"results": []}))
        with patch("services.adzuna.get_adzuna_app_id", return_value=""), patch(
            "services.adzuna.get_adzuna_app_key", return_value=SECRET
        ):
            with self.assertRaises(AdzunaCredentialsError) as caught:
                search_jobs(what="Python Developer", session=session)

        self.assertEqual(str(caught.exception), "ADZUNA_APP_ID is missing. Set it in the .env file.")
        self.assertNotIn(SECRET, str(caught.exception))
        self.assertEqual(session.calls, [])

    def test_unauthorized_response_hides_the_response_body(self):
        session = FakeSession(
            FakeResponse(status_code=401, text=f"bad key {SECRET}", payload={"error": SECRET})
        )
        with self._credentials():
            with self.assertRaises(AdzunaAuthError) as caught:
                search_jobs(what="Python Developer", session=session)

        self.assertEqual(caught.exception.status_code, 401)
        self.assertEqual(str(caught.exception), "Adzuna rejected the request with HTTP 401.")
        self.assertNotIn(SECRET, str(caught.exception))

    def test_timeout_does_not_keep_the_request_url(self):
        session = FakeSession(error=requests.Timeout(f"timed out for app_key={SECRET}"))
        with self._credentials():
            try:
                search_jobs(what="Python Developer", session=session)
            except AdzunaTimeoutError as exc:
                rendered = "".join(traceback.format_exception(exc))
                cause = exc.__cause__
                suppressed = exc.__suppress_context__
            else:
                self.fail("A timeout should raise AdzunaTimeoutError")

        self.assertNotIn(SECRET, rendered)
        self.assertIsNone(cause)
        self.assertTrue(suppressed)

    def test_malformed_json_uses_a_fixed_message(self):
        session = FakeSession(
            FakeResponse(json_error=requests.exceptions.JSONDecodeError(SECRET, SECRET, 0))
        )
        with self._credentials():
            with self.assertRaises(AdzunaError) as caught:
                search_jobs(what="Python Developer", session=session)

        self.assertEqual(str(caught.exception), "Adzuna returned a response that was not valid JSON.")
        self.assertNotIn(SECRET, str(caught.exception))
        self.assertNotIsInstance(caught.exception, AdzunaAuthError)

    def test_empty_results_are_a_successful_connection(self):
        session = FakeSession(FakeResponse(payload={"count": 0, "results": []}))
        with self._credentials():
            result = search_jobs(what="Python Developer", session=session)

        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.jobs, [])

    def test_http_failure_does_not_include_credentials_from_the_body(self):
        session = FakeSession(
            FakeResponse(status_code=500, text=SECRET, payload={"message": SECRET})
        )
        with self._credentials():
            with self.assertRaises(AdzunaError) as caught:
                search_jobs(what="Python Developer", session=session)

        self.assertEqual(caught.exception.status_code, 500)
        self.assertEqual(str(caught.exception), "Adzuna request failed with HTTP 500.")
        self.assertNotIn(SECRET, "".join(traceback.format_exception(caught.exception)))

    def test_date_sort_uses_the_documented_parameters_and_leaves_age_unset(self):
        session = FakeSession(FakeResponse(payload={"results": [listing()]}))
        with self._credentials():
            search_jobs(what="Python Developer", session=session, sort_by="date", sort_direction="down")

        params = session.calls[0][1]
        self.assertEqual(params["sort_by"], "date")
        self.assertEqual(params["sort_direction"], "down")
        self.assertNotIn("max_days_old", params)

    def test_predicted_salary_is_not_returned_as_a_real_figure(self):
        session = FakeSession(
            FakeResponse(
                payload={
                    "results": [
                        listing(salary_min=90000, salary_max=100000, salary_is_predicted=1, contract_type="permanent")
                    ]
                }
            )
        )
        with self._credentials():
            result = search_jobs(what="Python Developer", session=session)

        job = result.jobs[0]
        self.assertIsNone(job.salary_min)
        self.assertIsNone(job.salary_max)
        self.assertTrue(job.salary_is_predicted)
        self.assertEqual(job.contract_type, "permanent")
        self.assertIsNone(job.workplace)

    def test_rate_limit_is_reported_without_the_response_body(self):
        session = FakeSession(FakeResponse(status_code=429, text=SECRET))
        with self._credentials():
            with self.assertRaises(AdzunaRateLimitError) as caught:
                search_jobs(what="Python Developer", session=session)

        self.assertEqual(caught.exception.status_code, 429)
        self.assertNotIn(SECRET, str(caught.exception))

    def test_categories_keep_each_countrys_label_and_tag(self):
        session = FakeSession(
            FakeResponse(
                payload={
                    "results": [
                        {"label": "IT Jobs", "tag": "it-jobs"},
                        {"label": "Healthcare & Nursing Jobs", "tag": "healthcare-nursing-jobs"},
                        {"label": "", "tag": "ignored"},
                        {"tag": "missing-label"},
                    ]
                }
            )
        )
        with self._credentials():
            rows = list_categories(country="in", session=session)

        self.assertEqual([(item.country, item.label, item.tag) for item in rows], [
            ("in", "IT Jobs", "it-jobs"),
            ("in", "Healthcare & Nursing Jobs", "healthcare-nursing-jobs"),
        ])
        self.assertIn("/jobs/in/categories", session.calls[0][0])
        self.assertNotIn("category", session.calls[0][1])

    def test_empty_category_catalogue_is_not_an_error(self):
        session = FakeSession(FakeResponse(payload={"results": []}))
        with self._credentials():
            self.assertEqual(list_categories(country="gb", session=session), [])

    def test_category_search_uses_the_documented_tag_parameter(self):
        session = FakeSession(
            FakeResponse(
                payload={
                    "results": [
                        listing(
                            title="Staff Nurse",
                            category={"label": "Healthcare & Nursing Jobs", "tag": "healthcare-nursing-jobs"},
                        )
                    ]
                }
            )
        )
        with self._credentials():
            result = search_jobs(
                country="gb",
                category="healthcare-nursing-jobs",
                results_per_page=2,
                page=1,
                sort_by="date",
                sort_direction="down",
                session=session,
            )

        params = session.calls[0][1]
        self.assertEqual(params["category"], "healthcare-nursing-jobs")
        self.assertNotIn("what", params)
        self.assertEqual(params["sort_by"], "date")
        self.assertEqual(result.jobs[0].category_label, "Healthcare & Nursing Jobs")
        self.assertEqual(result.jobs[0].category_tag, "healthcare-nursing-jobs")
        self.assertEqual(result.jobs[0].title, "Staff Nurse")

    def test_category_catalogue_errors_hide_credentials(self):
        session = FakeSession(FakeResponse(status_code=429, text=SECRET))
        with self._credentials():
            with self.assertRaises(AdzunaRateLimitError) as caught:
                list_categories(country="gb", session=session)

        self.assertNotIn(SECRET, str(caught.exception))
        self.assertNotIn(SECRET, "".join(traceback.format_exception(caught.exception)))

    def _credentials(self):
        return patch.multiple(
            "services.adzuna",
            get_adzuna_app_id=lambda: APP_ID,
            get_adzuna_app_key=lambda: SECRET,
        )


if __name__ == "__main__":
    unittest.main()
