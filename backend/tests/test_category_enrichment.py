"""Category enrichment is planned without writing to Supabase."""

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import import_adzuna
from models import Base, Candidate, Job, SavedJob
from services.category_enrichment import (
    StoredIdentity,
    apply_category_plan,
    plan_category_enrichment,
)
from services.job_discovery import DiscoveredJob, DiscoverySummary, SearchAttempt
from services.job_schema import JOB_CATEGORY_STATEMENTS

WHEN = datetime(2026, 11, 22, 12, 0, tzinfo=timezone.utc)


def discovered(**overrides) -> DiscoveredJob:
    values = {
        "source": "adzuna",
        "external_job_id": "100",
        "country": "gb",
        "title": "Nurse",
        "company": "Hospital",
        "location": "York",
        "description": "Ward work",
        "description_status": "provider snippet",
        "source_url": "https://www.adzuna.co.uk/jobs/land/ad/100",
        "posted_at": WHEN,
        "posting_status": "recent",
        "salary_min": None,
        "salary_max": None,
        "salary_currency": None,
        "salary_status": "not supplied",
        "contract_type": None,
        "contract_time": None,
        "workplace": None,
        "queries": ("healthcare-nursing-jobs",),
        "categories": ("Healthcare & Nursing Jobs",),
        "category_label": "Healthcare & Nursing Jobs",
        "category_tag": "healthcare-nursing-jobs",
    }
    values.update(overrides)
    return DiscoveredJob(**values)


class EnrichmentTests(unittest.TestCase):
    def test_matching_uses_source_country_and_external_id(self):
        stored = [StoredIdentity("adzuna", "gb", "100")]
        jobs = [
            discovered(),
            discovered(external_job_id="100", country="in", title="Nurse India"),
            discovered(),
        ]

        plan = plan_category_enrichment(jobs, stored)

        self.assertEqual(plan.matched, 1)
        self.assertEqual(plan.enrichable, 1)
        self.assertEqual(plan.insertable, 1)
        self.assertEqual(plan.duplicates, 1)
        self.assertEqual(plan.stored_unmatched, 0)
        self.assertEqual(plan.actions[0].kind, "enrich")
        self.assertEqual(plan.actions[1].kind, "insert")
        self.assertEqual(plan.actions[1].country, "in")

    def test_a_missing_or_different_category_does_not_replace_stored_text(self):
        stored = [
            StoredIdentity("adzuna", "gb", "100", "Legal Jobs", "legal-jobs"),
            StoredIdentity("adzuna", "gb", "200", "IT Jobs", "it-jobs"),
        ]
        jobs = [
            discovered(category_label=None, category_tag=None),
            discovered(external_job_id="200", category_label="Sales Jobs", category_tag="sales-jobs"),
        ]

        plan = plan_category_enrichment(jobs, stored)

        self.assertEqual(plan.enrichable, 0)
        self.assertEqual(plan.already_categorised, 1)
        self.assertEqual(plan.category_conflicts, 1)
        self.assertEqual(plan.actions[0].category_tag, "legal-jobs")
        self.assertEqual(plan.actions[1].category_tag, "it-jobs")
        self.assertEqual(plan.missing_category, 1)
        self.assertEqual(plan.missing_skills, 2)

    def test_duplicate_catalogue_rows_are_stored_once(self):
        catalogue = [
            {"country": "gb", "label": "IT Jobs", "tag": "it-jobs"},
            {"country": "gb", "label": "IT Jobs", "tag": "it-jobs"},
            {"country": "in", "label": "IT Jobs", "tag": "it-jobs"},
        ]

        plan = plan_category_enrichment([], [], catalogue=catalogue)

        self.assertEqual(plan.catalogue, (("gb", "it-jobs", "IT Jobs"), ("in", "it-jobs", "IT Jobs")))

    def test_commit_fills_only_an_empty_category_and_keeps_the_saved_job(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine, tables=[Candidate.__table__, Job.__table__, SavedJob.__table__])
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE jobs ADD COLUMN category_label VARCHAR(200)"))
            connection.execute(text("ALTER TABLE jobs ADD COLUMN category_tag VARCHAR(80)"))
            connection.execute(
                text(
                    "CREATE TABLE provider_categories ("
                    "country VARCHAR(2) NOT NULL, tag VARCHAR(80) NOT NULL, label VARCHAR(200) NOT NULL, "
                    "PRIMARY KEY (country, tag))"
                )
            )
        session = sessionmaker(bind=engine)()
        candidate = Candidate(name="Ada Lovelace", email="ada@example.com", skills=[], preferred_roles=[], preferred_locations=[])
        session.add(candidate)
        session.flush()
        job = Job(
            title="Keep this title",
            company="Hospital",
            location="York",
            required_skills=["Care"],
            min_experience=3,
            source="adzuna",
            external_job_id="100",
            source_country="gb",
            source_url="https://www.adzuna.co.uk/jobs/land/ad/100",
            is_matchable=False,
            matchability_status="unmatchable",
            requirements_available=False,
        )
        session.add(job)
        session.flush()
        session.add(SavedJob(candidate_id=candidate.id, job_id=job.id))
        session.commit()
        job_id = job.id

        preview = apply_category_plan(session, [discovered(title="Replacement title")], catalogue=[], commit=False)
        self.assertFalse(preview.wrote)
        self.assertEqual(session.get(Job, job_id).title, "Keep this title")
        self.assertIsNone(session.execute(text("SELECT category_tag FROM jobs WHERE id = :id"), {"id": job_id}).scalar())

        plan = apply_category_plan(
            session,
            [
                discovered(title="Replacement title"),
                discovered(external_job_id="300", country="in", title="Teacher", category_label="Teaching Jobs", category_tag="teaching-jobs"),
            ],
            catalogue=[{"country": "gb", "label": "Healthcare & Nursing Jobs", "tag": "healthcare-nursing-jobs"}],
            commit=True,
            now=lambda: WHEN,
        )

        self.assertTrue(plan.wrote)
        stored = session.get(Job, job_id)
        self.assertEqual(stored.title, "Keep this title")
        self.assertEqual(stored.company, "Hospital")
        self.assertEqual(stored.required_skills, ["Care"])
        self.assertFalse(stored.is_matchable)
        self.assertEqual(session.execute(text("SELECT category_tag FROM jobs WHERE id = :id"), {"id": job_id}).scalar(), "healthcare-nursing-jobs")
        saved = session.scalar(select(SavedJob))
        self.assertEqual(saved.job_id, job_id)
        inserted = session.scalar(select(Job).where(Job.external_job_id == "300"))
        self.assertEqual(inserted.source_country, "in")
        self.assertFalse(inserted.is_matchable)
        self.assertEqual(inserted.required_skills, [])
        self.assertEqual(session.execute(text("SELECT category_tag FROM jobs WHERE external_job_id = '300'")).scalar(), "teaching-jobs")
        session.close()

    def test_category_schema_statements_do_not_delete_rows(self):
        text_sql = " ".join(JOB_CATEGORY_STATEMENTS).upper()
        self.assertNotIn("DROP ", text_sql)
        self.assertNotIn("DELETE ", text_sql)
        self.assertNotIn("TRUNCATE ", text_sql)
        self.assertIn("CATEGORY_LABEL", text_sql)
        self.assertIn("PROVIDER_CATEGORIES", text_sql)

    def test_enrichment_dry_run_does_not_commit(self):
        summary = DiscoverySummary(
            (),
            (discovered(),),
            1,
            1,
            0,
            ("gb",),
            (),
            1,
            1,
            0,
            0,
            {"gb": 1},
            {},
            1,
            1,
            0,
            0,
            0,
        )
        stored = ([StoredIdentity("adzuna", "gb", "100")], {"jobs": 98, "manual_jobs": 21, "adzuna_jobs": 77, "adzuna_unmatchable": 77, "saved_jobs": 6, "category_columns": False, "category_table": False})
        catalogue = (type("Category", (), {"country": "gb", "label": "Healthcare & Nursing Jobs", "tag": "healthcare-nursing-jobs"})(),)
        attempts = (SearchAttempt("gb", "", "categories", "success", 200, 1, None),)
        with patch("import_adzuna.collect_categories", return_value=(catalogue, attempts)), patch(
            "import_adzuna.discover_categories", return_value=summary
        ), patch("import_adzuna._read_enrichment_state", return_value=stored), patch(
            "import_adzuna.apply_category_plan", side_effect=AssertionError("commit path used")
        ), patch("database.SessionLocal", side_effect=AssertionError("session opened")):
            code = import_adzuna.main(
                ["--use-categories", "--enrich-stored", "--countries", "gb", "--limit-per-query", "2", "--dry-run"]
            )

        self.assertEqual(code, 0)

    def test_category_commit_is_refused_before_any_search_when_columns_are_missing(self):
        with patch("import_adzuna._category_columns_ready", return_value=False), patch(
            "import_adzuna.collect_categories", side_effect=AssertionError("searched")
        ), patch("database.SessionLocal", side_effect=AssertionError("session opened")):
            code = import_adzuna.main(["--use-categories", "--enrich-stored", "--commit"])

        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
