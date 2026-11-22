"""Discovery checks never call Adzuna or Supabase."""

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import import_adzuna
from services.adzuna import AdzunaError, AdzunaJob, AdzunaRateLimitError, AdzunaSearch, ProviderCategory
from services.job_discovery import (
    SearchAttempt,
    collect_categories,
    discover_categories,
    discover_jobs,
    sample_categories,
)
from services.search_catalog import ROLE_SEARCHES, RoleSearch

SECRET = "adzuna-secret-value"
NOW = datetime(2026, 11, 22, 12, 0, tzinfo=timezone.utc)


def job(**overrides) -> AdzunaJob:
    values = {
        "title": "Python Developer",
        "company": "Northwind",
        "location": "London",
        "created": "2026-11-20T09:00:00Z",
        "redirect_url": "https://www.adzuna.co.uk/jobs/land/ad/100",
        "external_id": "100",
        "description": "Build Python services.",
    }
    values.update(overrides)
    return AdzunaJob(**values)


def found(*jobs) -> AdzunaSearch:
    return AdzunaSearch(status_code=200, jobs=list(jobs))


class FakeSource:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def search_listings(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self.responses[(kwargs["country"], kwargs["query"])]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class _CategorySource:
    def __init__(self, responses):
        self.responses = responses

    def list_categories(self, *, country):
        outcome = self.responses[country]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class _SearchSource:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def search_listings(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self.responses[(kwargs["country"], kwargs["category"])]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class DiscoveryTests(unittest.TestCase):
    def test_several_roles_and_both_countries_are_searched(self):
        searches = [
            RoleSearch("Software development", "Python Developer"),
            RoleSearch("Data and AI", "Data Analyst"),
        ]
        source = FakeSource(
            {
                ("gb", "Python Developer"): found(job()),
                ("gb", "Data Analyst"): found(job(title="Data Analyst", external_id="200", location="Manchester")),
                ("in", "Python Developer"): found(job(title="Python Developer", external_id="300", location="Bengaluru", redirect_url="https://www.adzuna.co.in/jobs/land/ad/300")),
                ("in", "Data Analyst"): found(job(title="Data Analyst", external_id="400", location="Pune", redirect_url="https://www.adzuna.co.in/jobs/land/ad/400")),
            }
        )

        summary = discover_jobs(
            countries=["gb", "in"],
            searches=searches,
            limit=3,
            source=source,
            pause_seconds=0,
            now=lambda: NOW,
        )

        self.assertEqual(summary.requests_attempted, 4)
        self.assertEqual(summary.requests_succeeded, 4)
        self.assertEqual(summary.countries_succeeded, ("gb", "in"))
        self.assertEqual(summary.countries_failed, ())
        self.assertEqual(summary.unique, 4)
        self.assertEqual(summary.by_country, {"gb": 2, "in": 2})
        self.assertFalse(summary.wrote)
        self.assertEqual(source.calls[0]["sort_by"], "date")
        self.assertEqual(source.calls[0]["sort_direction"], "down")
        self.assertIsNone(source.calls[0]["max_days_old"])

    def test_an_india_failure_does_not_stop_the_united_kingdom(self):
        source = FakeSource(
            {
                ("gb", "Python Developer"): found(job()),
                ("in", "Python Developer"): AdzunaRateLimitError("Adzuna rate limit reached with HTTP 429.", 429),
            }
        )

        summary = discover_jobs(
            countries=["gb", "in"],
            searches=[RoleSearch("Software development", "Python Developer")],
            limit=3,
            source=source,
            pause_seconds=0,
            now=lambda: NOW,
        )

        self.assertEqual(summary.countries_succeeded, ("gb",))
        self.assertEqual(summary.countries_failed, ("in",))
        self.assertEqual(summary.unique, 1)
        self.assertEqual(summary.jobs[0].country, "gb")
        self.assertEqual(summary.requests_failed, 1)

    def test_the_same_listing_from_two_queries_is_kept_once(self):
        shared = job()
        source = FakeSource(
            {
                ("gb", "Python Developer"): found(shared),
                ("gb", "Backend Developer"): found(shared),
            }
        )

        summary = discover_jobs(
            countries=["gb"],
            searches=[
                RoleSearch("Software development", "Python Developer"),
                RoleSearch("Software development", "Backend Developer"),
            ],
            limit=3,
            source=source,
            pause_seconds=0,
            now=lambda: NOW,
        )

        self.assertEqual(summary.fetched, 2)
        self.assertEqual(summary.unique, 1)
        self.assertEqual(summary.cross_query_duplicates, 1)
        self.assertEqual(summary.jobs[0].queries, ("Python Developer", "Backend Developer"))
        self.assertEqual(summary.by_category["Software development"], 1)

    def test_same_provider_id_with_a_different_url_is_not_merged(self):
        source = FakeSource(
            {
                ("gb", "Python Developer"): found(
                    job(),
                    job(location="Bristol", redirect_url="https://www.adzuna.co.uk/jobs/land/ad/100-other"),
                )
            }
        )

        summary = discover_jobs(
            countries=["gb"],
            searches=[RoleSearch("Software development", "Python Developer")],
            limit=3,
            source=source,
            pause_seconds=0,
            now=lambda: NOW,
        )

        self.assertEqual(summary.unique, 2)
        self.assertEqual(summary.kept_separate, 1)
        self.assertEqual({item.location for item in summary.jobs}, {"London", "Bristol"})

    def test_tracking_parameters_do_not_make_a_second_copy(self):
        source = FakeSource(
            {
                ("gb", "Python Developer"): found(job(redirect_url="https://www.adzuna.co.uk/jobs/land/ad/100?se=one")),
                ("gb", "Backend Developer"): found(job(redirect_url="https://www.adzuna.co.uk/jobs/land/ad/100?se=two")),
            }
        )

        summary = discover_jobs(
            countries=["gb"],
            searches=[
                RoleSearch("Software development", "Python Developer"),
                RoleSearch("Software development", "Backend Developer"),
            ],
            limit=3,
            source=source,
            pause_seconds=0,
            now=lambda: NOW,
        )

        self.assertEqual(summary.unique, 1)
        self.assertEqual(summary.cross_query_duplicates, 1)
        self.assertEqual(summary.kept_separate, 0)
        self.assertTrue(summary.jobs[0].source_url.endswith("se=one"))

    def test_missing_optional_fields_and_posting_age_are_labelled(self):
        source = FakeSource(
            {
                ("gb", "Python Developer"): found(
                    job(description=None, created=None, salary_is_predicted=True),
                    job(external_id="201", created="2026-01-01T00:00:00Z", salary_min=40000, salary_max=50000),
                )
            }
        )

        summary = discover_jobs(
            countries=["gb"],
            searches=[RoleSearch("Software development", "Python Developer")],
            limit=3,
            source=source,
            pause_seconds=0,
            now=lambda: NOW,
        )

        undated, older = summary.jobs
        self.assertEqual(undated.description_status, "not supplied")
        self.assertEqual(undated.posting_status, "not supplied")
        self.assertEqual(undated.salary_status, "predicted figure ignored")
        self.assertIsNone(undated.salary_min)
        self.assertEqual(older.posting_status, "older")
        self.assertEqual(older.salary_status, "supplied")
        self.assertIsNone(older.salary_currency)
        self.assertEqual(summary.missing_required_skills, 2)
        self.assertEqual(summary.old_listings, 1)
        self.assertEqual(summary.undated_listings, 1)
        self.assertEqual(summary.missing_descriptions, 1)

    def test_unexpected_provider_errors_do_not_keep_credentials(self):
        source = FakeSource({("gb", "Python Developer"): RuntimeError(f"app_key={SECRET}")})

        with patch("services.job_discovery.get_adzuna_app_key", return_value=SECRET):
            summary = discover_jobs(
                countries=["gb"],
                searches=[RoleSearch("Software development", "Python Developer")],
                limit=3,
                source=source,
                pause_seconds=0,
                now=lambda: NOW,
            )

        self.assertEqual(summary.attempts[0].error_message, "The Adzuna request could not be completed.")
        self.assertNotIn(SECRET, summary.attempts[0].error_message)
        self.assertFalse(summary.wrote)

    def test_catalog_contains_the_requested_roles_without_synonym_duplicates(self):
        queries = [item.query for item in ROLE_SEARCHES]
        self.assertIn("Software Engineer", queries)
        self.assertIn("AI/ML Intern", queries)
        self.assertIn("Graduate Software Engineer", queries)
        self.assertNotIn("Python Programmer", queries)
        self.assertEqual(len(queries), len(set(queries)))

    def test_single_country_command_still_uses_the_original_import(self):
        with patch("import_adzuna.import_adzuna_jobs") as single, patch("import_adzuna.discover_jobs") as multi:
            single.return_value = _single_summary()
            code = import_adzuna.main(["--country", "gb", "--what", "Python Developer", "--limit", "5", "--dry-run"])

        self.assertEqual(code, 0)
        single.assert_called_once()
        self.assertEqual(single.call_args.kwargs["country"], "gb")
        self.assertEqual(single.call_args.kwargs["what"], "Python Developer")
        self.assertFalse(single.call_args.kwargs["commit"])
        multi.assert_not_called()

    def test_multi_country_dry_run_classifies_without_writing(self):
        with patch("import_adzuna.discover_jobs", return_value=_discovery_summary()) as multi, patch(
            "import_adzuna._read_catalogue_state", return_value=_stored_state()
        ), patch("database.SessionLocal", side_effect=AssertionError("database opened")):
            code = import_adzuna.main(
                ["--countries", "gb", "in", "--queries", "Python Developer", "--limit-per-query", "3", "--sort-by", "date", "--dry-run"]
            )

        self.assertEqual(code, 0)
        self.assertEqual(multi.call_args.kwargs["countries"], ["gb", "in"])
        self.assertEqual(multi.call_args.kwargs["limit"], 3)
        self.assertEqual(multi.call_args.kwargs["sort_by"], "date")
        self.assertFalse(multi.call_args.kwargs.get("commit", False))

    def test_catalogue_commit_waits_until_the_migration_is_ready(self):
        with patch("import_adzuna.discover_jobs", side_effect=AssertionError("searched")) as multi, patch(
            "import_adzuna._read_catalogue_state", return_value=_stored_state()
        ), patch("database.SessionLocal", side_effect=AssertionError("database opened")):
            code = import_adzuna.main(["--countries", "gb", "in", "--use-catalog", "--commit"])

        self.assertEqual(code, 2)
        multi.assert_not_called()

    def test_category_catalogues_stay_separate_by_country(self):
        source = _CategorySource(
            {
                "gb": [ProviderCategory("gb", "IT Jobs", "it-jobs"), ProviderCategory("gb", "Teaching Jobs", "teaching-jobs")],
                "in": [ProviderCategory("in", "Healthcare & Nursing Jobs", "healthcare-nursing-jobs")],
            }
        )

        categories, attempts = collect_categories(["gb", "in"], source=source, pause_seconds=0)

        self.assertEqual([item.tag for item in categories if item.country == "gb"], ["it-jobs", "teaching-jobs"])
        self.assertEqual([item.tag for item in categories if item.country == "in"], ["healthcare-nursing-jobs"])
        self.assertEqual(len(attempts), 2)
        self.assertTrue(all(item.status == "success" for item in attempts))

    def test_an_empty_category_list_is_kept(self):
        source = _CategorySource({"gb": []})

        categories, attempts = collect_categories(["gb"], source=source, pause_seconds=0)

        self.assertEqual(categories, ())
        self.assertEqual(attempts[0].status, "success")
        self.assertEqual(attempts[0].fetched, 0)

    def test_a_category_failure_does_not_stop_the_other_country(self):
        source = _CategorySource(
            {
                "gb": [ProviderCategory("gb", "Sales Jobs", "sales-jobs")],
                "in": AdzunaRateLimitError("Adzuna rate limit reached with HTTP 429.", 429),
            }
        )

        categories, attempts = collect_categories(["gb", "in"], source=source, pause_seconds=0)

        self.assertEqual([item.country for item in categories], ["gb"])
        self.assertEqual(attempts[1].status, "error")
        self.assertEqual(attempts[1].country, "in")

    def test_the_same_listing_in_two_categories_is_kept_once(self):
        shared = job(category_label="Sales Jobs", category_tag="sales-jobs")
        source = _SearchSource(
            {
                ("gb", "sales-jobs"): found(shared),
                ("gb", "retail-jobs"): found(shared),
            }
        )
        categories = [
            ProviderCategory("gb", "Sales Jobs", "sales-jobs"),
            ProviderCategory("gb", "Retail Jobs", "retail-jobs"),
        ]

        summary = discover_categories(
            countries=["gb"],
            categories=categories,
            limit=2,
            source=source,
            pause_seconds=0,
            now=lambda: NOW,
        )

        self.assertEqual(summary.unique, 1)
        self.assertEqual(summary.cross_query_duplicates, 1)
        self.assertEqual(summary.jobs[0].categories, ("Sales Jobs", "Retail Jobs"))
        self.assertEqual(summary.jobs[0].category_tag, "sales-jobs")
        self.assertFalse(summary.wrote)
        self.assertEqual(source.calls[0]["category"], "sales-jobs")
        self.assertEqual(source.calls[0]["query"], "")
        self.assertEqual(source.calls[0]["sort_by"], "date")
        self.assertEqual(source.calls[0]["page"], 1)

    def test_category_samples_are_spread_across_the_returned_catalogue(self):
        rows = [ProviderCategory("gb", f"Label {index}", f"tag-{index}") for index in range(6)]

        chosen = sample_categories(rows, 3)

        self.assertEqual([item.tag for item in chosen], ["tag-0", "tag-2", "tag-5"])

    def test_category_dry_run_does_not_open_the_database(self):
        with patch("import_adzuna.collect_categories", return_value=((), ())) as collect, patch(
            "import_adzuna.discover_categories", side_effect=AssertionError("searched")
        ), patch("database.SessionLocal", side_effect=AssertionError("database opened")):
            code = import_adzuna.main(["--use-categories", "--countries", "gb", "in", "--dry-run"])

        self.assertEqual(code, 1)
        collect.assert_called_once()

    def test_category_commit_is_refused_before_any_request(self):
        with patch("import_adzuna.collect_categories", side_effect=AssertionError("requested")) as collect, patch(
            "database.SessionLocal", side_effect=AssertionError("database opened")
        ):
            code = import_adzuna.main(["--use-categories", "--commit"])

        self.assertEqual(code, 2)
        collect.assert_not_called()

    def test_every_returned_category_is_searched_with_its_country_and_tag(self):
        categories = [
            ProviderCategory("gb", "IT Jobs", "it-jobs"),
            ProviderCategory("gb", "Unknown", "unknown"),
            ProviderCategory("in", "Legal Jobs", "legal-jobs"),
        ]
        source = _SearchSource(
            {
                ("gb", "it-jobs"): found(job(category_label="IT Jobs", category_tag="it-jobs")),
                ("gb", "unknown"): found(),
                ("in", "legal-jobs"): found(
                    job(title="Solicitor", external_id="501", location="Mumbai", category_label="Legal Jobs", category_tag="legal-jobs")
                ),
            }
        )

        summary = discover_categories(
            countries=["gb", "in"],
            categories=categories,
            limit=2,
            source=source,
            pause_seconds=0,
            now=lambda: NOW,
        )

        self.assertEqual(
            [(call["country"], call["category"], call["query"], call["sort_by"], call["sort_direction"], call["page"]) for call in source.calls],
            [
                ("gb", "it-jobs", "", "date", "down", 1),
                ("gb", "unknown", "", "date", "down", 1),
                ("in", "legal-jobs", "", "date", "down", 1),
            ],
        )
        self.assertEqual(summary.requests_succeeded, 3)
        self.assertEqual(summary.unique, 2)
        self.assertEqual([item.fetched for item in summary.attempts], [1, 0, 1])
        self.assertEqual(summary.attempts[1].status, "success")

    def test_one_category_error_does_not_drop_the_other_results(self):
        source = _SearchSource(
            {
                ("gb", "it-jobs"): AdzunaError("Adzuna request failed with HTTP 500.", 500),
                ("in", "teaching-jobs"): found(job(title="Teacher", external_id="700", location="Delhi")),
            }
        )

        summary = discover_categories(
            countries=["gb", "in"],
            categories=[
                ProviderCategory("gb", "IT Jobs", "it-jobs"),
                ProviderCategory("in", "Teaching Jobs", "teaching-jobs"),
            ],
            limit=2,
            source=source,
            pause_seconds=0,
            now=lambda: NOW,
        )

        self.assertEqual(summary.requests_failed, 1)
        self.assertEqual(summary.unique, 1)
        self.assertEqual(summary.jobs[0].country, "in")
        self.assertEqual(summary.attempts[0].status_code, 500)

    def test_a_rate_limit_is_retried_before_the_listing_is_kept(self):
        calls = {"count": 0}

        class SlowSource:
            def search_listings(self, **kwargs):
                calls["count"] += 1
                if calls["count"] < 3:
                    raise AdzunaRateLimitError("Adzuna rate limit reached with HTTP 429.", 429)
                return found(job(category_label="Sales Jobs", category_tag="sales-jobs"))

        waits = []
        summary = discover_categories(
            countries=["gb"],
            categories=[ProviderCategory("gb", "Sales Jobs", "sales-jobs")],
            limit=2,
            source=SlowSource(),
            pause_seconds=1,
            sleep=waits.append,
            now=lambda: NOW,
        )

        self.assertEqual(calls["count"], 3)
        self.assertEqual(waits, [1, 2])
        self.assertEqual(summary.unique, 1)
        self.assertEqual(summary.requests_succeeded, 1)
        self.assertEqual(summary.http_requests, 3)
        self.assertNotIn("app_key", summary.attempts[0].error_message or "")

    def test_repeated_rate_limits_stop_later_categories_and_keep_earlier_listings(self):
        class LimitedSource:
            def __init__(self):
                self.calls = []

            def search_listings(self, **kwargs):
                self.calls.append(kwargs["category"])
                if kwargs["category"] == "kept":
                    return found(job(title="Nurse", external_id="800", category_label="Healthcare", category_tag="kept"))
                raise AdzunaRateLimitError("Adzuna rate limit reached with HTTP 429.", 429)

        source = LimitedSource()
        summary = discover_categories(
            countries=["gb"],
            categories=[
                ProviderCategory("gb", "Healthcare", "kept"),
                ProviderCategory("gb", "One", "one"),
                ProviderCategory("gb", "Two", "two"),
                ProviderCategory("gb", "Three", "three"),
                ProviderCategory("gb", "Four", "four"),
            ],
            limit=2,
            source=source,
            pause_seconds=0,
            now=lambda: NOW,
        )

        self.assertEqual(source.calls, ["kept", "one", "one", "one", "two", "two", "two", "three", "three", "three"])
        self.assertEqual(summary.jobs[0].title, "Nurse")
        self.assertEqual(summary.requests_failed, 3)
        self.assertEqual(summary.attempts[-1].status, "stopped")
        self.assertEqual(summary.attempts[-1].query, "four")
        self.assertNotIn("adzuna-secret", summary.attempts[-1].error_message)

    def test_missing_category_fields_stay_missing(self):
        source = _SearchSource(
            {
                ("gb", "legal-jobs"): found(
                    job(
                        title="Solicitor",
                        description=None,
                        redirect_url=None,
                        created="2026-01-01T00:00:00Z",
                        salary_min=None,
                        salary_max=None,
                        category_label="Legal Jobs",
                        category_tag="legal-jobs",
                    )
                )
            }
        )

        summary = discover_categories(
            countries=["gb"],
            categories=[ProviderCategory("gb", "Legal Jobs", "legal-jobs")],
            limit=2,
            source=source,
            pause_seconds=0,
            now=lambda: NOW,
        )

        listing = summary.jobs[0]
        self.assertEqual(listing.description_status, "not supplied")
        self.assertIsNone(listing.source_url)
        self.assertEqual(listing.posting_status, "older")
        self.assertIsNone(listing.salary_currency)
        self.assertEqual(listing.salary_status, "not supplied")
        self.assertIsNone(listing.contract_time)
        self.assertIsNone(listing.workplace)
        self.assertEqual(summary.missing_required_skills, 1)
        self.assertEqual(summary.missing_descriptions, 1)
        self.assertEqual(summary.old_listings, 1)

    def test_category_errors_do_not_keep_credentials(self):
        class Broken:
            def search_listings(self, **kwargs):
                raise RuntimeError(f"app_key={SECRET}")

        with patch("services.job_discovery.get_adzuna_app_key", return_value=SECRET):
            summary = discover_categories(
                countries=["gb"],
                categories=[ProviderCategory("gb", "IT Jobs", "it-jobs")],
                limit=2,
                source=Broken(),
                pause_seconds=0,
                now=lambda: NOW,
            )

        self.assertEqual(summary.attempts[0].error_message, "The Adzuna request could not be completed.")
        self.assertNotIn(SECRET, summary.attempts[0].error_message)
        self.assertFalse(summary.wrote)

    def test_a_full_category_dry_run_searches_every_tag_without_a_database(self):
        rows = (
            ProviderCategory("gb", "IT Jobs", "it-jobs"),
            ProviderCategory("gb", "Unknown", "unknown"),
            ProviderCategory("in", "Legal Jobs", "legal-jobs"),
        )
        attempts = (
            SearchAttempt("gb", "", "categories", "success", 200, 2, None),
            SearchAttempt("in", "", "categories", "success", 200, 1, None),
        )
        with patch("import_adzuna.collect_categories", return_value=(rows, attempts)), patch(
            "import_adzuna.discover_categories", return_value=_discovery_summary()
        ) as discover, patch("database.SessionLocal", side_effect=AssertionError("database opened")):
            code = import_adzuna.main(
                ["--use-categories", "--countries", "gb", "in", "--limit-per-query", "2", "--pages", "1", "--sort-by", "date", "--dry-run"]
            )

        self.assertEqual(code, 0)
        selected = discover.call_args.kwargs["categories"]
        self.assertEqual([(item.country, item.tag) for item in selected], [("gb", "it-jobs"), ("gb", "unknown"), ("in", "legal-jobs")])
        self.assertEqual(discover.call_args.kwargs["limit"], 2)
        self.assertEqual(discover.call_args.kwargs["sort_by"], "date")

    def test_catalogue_commit_uses_the_same_search_as_the_dry_run(self):
        seen = []

        def capture(**kwargs):
            seen.append(kwargs)
            return _discovery_summary()

        ready = _stored_state()
        ready["schema_ready"] = True
        with patch("import_adzuna.discover_jobs", side_effect=capture), patch(
            "import_adzuna._read_catalogue_state", return_value=ready
        ), patch("import_adzuna.import_catalogue") as save, patch("database.SessionLocal") as sessions:
            sessions.return_value.close.return_value = None
            save.return_value = _catalogue_plan()
            dry = import_adzuna.main(
                ["--countries", "gb", "in", "--use-catalog", "--limit-per-query", "3", "--sort-by", "date", "--dry-run"]
            )
            committed = import_adzuna.main(
                ["--countries", "gb", "in", "--use-catalog", "--limit-per-query", "3", "--sort-by", "date", "--commit"]
            )

        self.assertEqual(dry, 0)
        self.assertEqual(committed, 0)
        self.assertEqual(seen[0]["countries"], seen[1]["countries"])
        self.assertEqual(seen[0]["limit"], seen[1]["limit"])
        self.assertEqual(seen[0]["sort_by"], seen[1]["sort_by"])
        self.assertEqual([item.query for item in seen[0]["searches"]], [item.query for item in ROLE_SEARCHES])
        self.assertEqual([item.query for item in seen[1]["searches"]], [item.query for item in ROLE_SEARCHES])
        self.assertEqual(len(seen[0]["searches"]), 16)
        self.assertFalse(save.call_args.kwargs["commit"] is False)
        self.assertTrue(save.call_args.kwargs["commit"])


def _single_summary():
    from services.job_import import ImportSummary

    return ImportSummary("success", "gb", "Python Developer", 0, 0, 0, 0, 0, False, None, ())


def _discovery_summary():
    from services.job_discovery import DiscoverySummary

    return DiscoverySummary((), (), 1, 1, 0, ("gb", "in"), (), 0, 0, 0, 0, {}, {}, 0, 0, 0, 0, 0)


def _stored_state():
    return {
        "readable": True,
        "schema_ready": False,
        "jobs": 21,
        "manual_jobs": 21,
        "saved_jobs": 1,
        "orphan_saved_jobs": 0,
        "adzuna_jobs": 0,
        "unique_index": False,
        "saved_foreign_key": True,
        "keys": set(),
    }


def _catalogue_plan():
    from services.job_import import CatalogueSummary

    return CatalogueSummary("success", 0, 0, 0, 0, 0, True, True, True, None)


if __name__ == "__main__":
    unittest.main()
