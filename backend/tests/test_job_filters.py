"""Discover filters use stored fields and the provider catalogue. No database writes."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.adzuna import AdzunaError, ProviderCategory
from services.category_catalogue import cached_categories, clear_category_cache
from services.job_filters import build_filter_metadata, filter_jobs, salary_needs_currency, search_from_params

SECRET = "adzuna-secret-value"


def listing(**overrides) -> dict:
    job = {
        "id": 1,
        "title": "Python Developer",
        "company": "Northwind",
        "location": "London",
        "required_skills": ["Python"],
        "min_experience": 2,
        "source_country": "gb",
        "is_matchable": True,
        "requirements_available": True,
    }
    job.update(overrides)
    return job


class FilterTests(unittest.TestCase):
    def test_a_title_does_not_choose_an_industry(self):
        rows = [
            listing(title="Python Developer"),
            listing(id=2, title="Solicitor", category_label="Legal Jobs", category_tag="legal-jobs", location="York"),
        ]

        legal = filter_jobs(rows, search_from_params({"category": "legal-jobs"}))
        missing = filter_jobs(rows, search_from_params({"category": "unspecified"}))
        technology = filter_jobs(rows, search_from_params({"category": "it-jobs"}))

        self.assertEqual([item["id"] for item in legal], [2])
        self.assertEqual([item["id"] for item in missing], [1])
        self.assertEqual(technology, [])

    def test_country_location_and_text_filters_combine(self):
        rows = [
            listing(location="Bengaluru, Karnataka", source_country="in", id=1),
            listing(id=2, title="Nurse", location="Manchester", source_country="gb", required_skills=["Care"]),
        ]

        found = filter_jobs(
            rows,
            search_from_params({"country": "IN", "location": "karnataka", "q": "python"}),
        )

        self.assertEqual([item["id"] for item in found], [1])

    def test_workplace_and_employment_use_only_stored_values(self):
        rows = [
            listing(id=1, title="Remote Developer", workplace=None, contract_time=None),
            listing(id=2, workplace="remote", contract_time="full_time"),
            listing(id=3, workplace="hybrid", contract_type="internship", title="Intern"),
            listing(id=4, workplace="on-site", contract_type="permanent"),
        ]

        self.assertEqual([item["id"] for item in filter_jobs(rows, search_from_params({"workplace": "remote"}))], [2])
        self.assertEqual([item["id"] for item in filter_jobs(rows, search_from_params({"workplace": "onsite"}))], [4])
        self.assertEqual([item["id"] for item in filter_jobs(rows, search_from_params({"employment": "internship"}))], [3])
        self.assertEqual(filter_jobs(rows, search_from_params({"employment": "temporary"})), [])

    def test_unknown_experience_stays_out_of_the_year_bands(self):
        rows = [
            listing(id=1, min_experience=0),
            listing(id=2, min_experience=4),
            listing(id=3, min_experience=6),
            listing(id=4, min_experience=0, is_matchable=False, requirements_available=False, title="Imported"),
        ]

        self.assertEqual([item["id"] for item in filter_jobs(rows, search_from_params({"experience": "entry"}))], [1])
        self.assertEqual([item["id"] for item in filter_jobs(rows, search_from_params({"experience": "0-2"}))], [1])
        self.assertEqual([item["id"] for item in filter_jobs(rows, search_from_params({"experience": "3-5"}))], [2])
        self.assertEqual([item["id"] for item in filter_jobs(rows, search_from_params({"experience": "5plus"}))], [3])
        self.assertEqual([item["id"] for item in filter_jobs(rows, search_from_params({"experience": "unspecified"}))], [4])

    def test_salary_filters_do_not_mix_currencies(self):
        rows = [
            listing(id=1, salary_min=40000, salary_currency="GBP"),
            listing(id=2, salary_min=900000, salary_currency="INR"),
            listing(id=3, salary_min=50000, salary_currency=None),
        ]

        pounds = filter_jobs(rows, search_from_params({"salary_currency": "GBP", "salary_min": "30000", "salary_max": "50000"}))
        self.assertEqual([item["id"] for item in pounds], [1])
        self.assertTrue(salary_needs_currency(search_from_params({"salary_min": 10})))

    def test_newest_sort_uses_the_posting_date(self):
        rows = [
            listing(id=1, posted_at="2026-11-01T00:00:00Z"),
            listing(id=2, posted_at=None),
            listing(id=3, posted_at="2026-11-22T00:00:00Z"),
        ]

        ordered = filter_jobs(rows, search_from_params({"sort": "newest"}))

        self.assertEqual([item["id"] for item in ordered], [3, 1, 2])

    def test_metadata_uses_catalogue_labels_and_only_stored_facts(self):
        categories = [
            {"country": "gb", "label": "IT Jobs", "tag": "it-jobs"},
            {"country": "in", "label": "IT Jobs", "tag": "it-jobs"},
            {"country": "in", "label": "Legal Jobs", "tag": "legal-jobs"},
        ]
        jobs = [
            listing(
                workplace="remote",
                contract_time="full_time",
                salary_min=10,
                salary_currency="GBP",
                source_country="us",
                category_label="IT Jobs",
                category_tag="it-jobs",
            ),
            listing(id=2, category_label="Legal Jobs", category_tag="legal-jobs", source_country="gb"),
        ]
        categories.append({"country": "gb", "label": "Sales Jobs", "tag": "sales-jobs"})

        meta = build_filter_metadata(jobs, categories)

        self.assertEqual([item["label"] for item in meta["categories"]], ["IT Jobs", "Legal Jobs"])
        self.assertEqual(meta["countries"][0]["value"], "gb")
        self.assertIn({"value": "us", "label": "United States"}, meta["countries"])
        self.assertEqual(meta["workplaces"], [{"value": "remote", "label": "Remote"}])
        self.assertEqual(meta["employment_types"], [{"value": "full_time", "label": "Full-time"}])
        self.assertEqual(meta["salary_currencies"], ["GBP"])
        self.assertNotIn("relevance", [item["value"] for item in meta["sorts"]])
        self.assertEqual(meta["category_status"], "ready")

    def test_category_catalogue_is_cached_per_country_and_hides_secrets(self):
        clear_category_cache()

        class Source:
            def __init__(self):
                self.calls = []

            def list_categories(self, *, country):
                self.calls.append(country)
                if country == "gb":
                    return [ProviderCategory("gb", "Teaching Jobs", "teaching-jobs")]
                raise AdzunaError(f"Adzuna request failed with {SECRET}", 500)

        source = Source()
        with patch("services.job_discovery.get_adzuna_app_key", return_value=SECRET):
            first, error = cached_categories(source=source, sleep=lambda _seconds: None, now=lambda: 10, countries=("gb", "in"))
            second, _error = cached_categories(source=source, sleep=lambda _seconds: None, now=lambda: 11, countries=("gb", "in"))

        self.assertEqual(source.calls, ["gb", "in"])
        self.assertEqual(first, [{"country": "gb", "label": "Teaching Jobs", "tag": "teaching-jobs"}])
        self.assertEqual(second, first)
        self.assertNotIn(SECRET, error or "")
        stored = build_filter_metadata(
            [{"category_tag": "teaching-jobs", "category_label": ""}],
            first,
            error,
        )
        self.assertEqual(stored["categories"], [{"value": "teaching-jobs", "label": "Teaching Jobs"}])
        self.assertEqual(stored["category_status"], "partial")
        self.assertEqual(build_filter_metadata([], first, error)["category_status"], "unavailable")
        clear_category_cache()

    def test_detail_filters_come_only_from_supplied_values(self):
        empty = build_filter_metadata([])
        self.assertEqual(empty["workplaces"], [])
        self.assertEqual(empty["employment_types"], [])
        self.assertEqual(empty["experience"], [])

        missing = build_filter_metadata(
            [
                listing(
                    workplace="",
                    contract_time="",
                    contract_type=None,
                    min_experience=0,
                    is_matchable=False,
                    requirements_available=False,
                    description="5 years of Python in a remote internship",
                )
            ]
        )
        self.assertEqual(missing["workplaces"], [])
        self.assertEqual(missing["employment_types"], [])
        self.assertEqual(missing["experience"], [])

        populated = build_filter_metadata(
            [
                listing(workplace="remote", contract_time="full_time", min_experience=0),
                listing(id=2, workplace="on-site", contract_type="permanent", min_experience=6),
                listing(
                    id=3,
                    source="jooble",
                    contract_time="contract",
                    min_experience=0,
                    is_matchable=False,
                    requirements_available=False,
                ),
            ]
        )
        self.assertEqual(
            [item["value"] for item in populated["workplaces"]],
            ["remote", "onsite"],
        )
        self.assertEqual(
            [item["value"] for item in populated["employment_types"]],
            ["full_time", "permanent", "contract"],
        )
        self.assertEqual(
            [item["value"] for item in populated["experience"]],
            ["any", "entry", "0-2", "5plus"],
        )
        self.assertNotIn("unspecified", [item["value"] for item in populated["experience"]])

        combined = filter_jobs(
            [
                listing(id=1, source_country="in", category_tag="it-jobs", location="Bengaluru", workplace="remote"),
                listing(id=2, source_country="gb", category_tag="legal-jobs", location="London", workplace="onsite"),
                listing(id=3, source_country="in", category_tag="it-jobs", location="Pune"),
            ],
            search_from_params(
                {"country": "in", "category": "it-jobs", "location": "ben", "workplace": "remote", "q": "Python"}
            ),
        )
        self.assertEqual([item["id"] for item in combined], [1])

    def test_matching_weights_stay_70_20_10(self):
        from types import SimpleNamespace

        from services.matching import score_job

        score = score_job(
            SimpleNamespace(skills=["Python"], preferred_roles=["Developer"], preferred_locations=["London"]),
            SimpleNamespace(
                title="Python Developer",
                location="London",
                required_skills=["Python"],
                requirements_available=True,
                is_matchable=True,
            ),
        )
        self.assertEqual((score.skill_score, score.role_score, score.location_score, score.total_score), (70.0, 20.0, 10.0, 100.0))


if __name__ == "__main__":
    unittest.main()
