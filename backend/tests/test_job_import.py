"""Import checks use a temporary SQLite database, never Supabase."""

import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models import Base, Candidate, Job, JobSyncLog, SavedJob
from services.adzuna import AdzunaError, AdzunaJob, AdzunaSearch
from services.job_discovery import DiscoveredJob, DiscoverySummary, SearchAttempt
from services.job_import import import_adzuna_jobs, import_catalogue
from services.job_schema import JOB_SOURCE_STATEMENTS

SECRET = "adzuna-secret-value"
WHEN = datetime(2026, 11, 21, 12, 0, tzinfo=timezone.utc)


def listing(**overrides) -> AdzunaJob:
    values = {
        "title": "Python Developer",
        "company": "Northwind",
        "location": "London",
        "created": "2026-11-21T09:00:00Z",
        "redirect_url": "https://www.adzuna.co.uk/jobs/land/ad/100",
        "external_id": "100",
        "description": "Build Python services.",
    }
    values.update(overrides)
    return AdzunaJob(**values)


def search_for(*jobs, error=None):
    def search(**_kwargs):
        if error is not None:
            raise error
        return AdzunaSearch(status_code=200, jobs=list(jobs))

    return search


class ImportTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        self.session = sessionmaker(bind=engine)()

    def tearDown(self):
        self.session.close()

    def test_new_external_job_is_inserted_with_provider_fields_only(self):
        summary = self._import(search_for(listing()), commit=True)

        job = self.session.scalar(select(Job))
        self.assertEqual(summary.inserted, 1)
        self.assertEqual(summary.updated, 0)
        self.assertTrue(summary.wrote)
        self.assertEqual(job.title, "Python Developer")
        self.assertEqual(job.company, "Northwind")
        self.assertEqual(job.location, "London")
        self.assertEqual(job.description, "Build Python services.")
        self.assertEqual(job.source, "adzuna")
        self.assertEqual(job.external_job_id, "100")
        self.assertEqual(job.source_country, "gb")
        self.assertEqual(job.source_url, "https://www.adzuna.co.uk/jobs/land/ad/100")
        self.assertEqual(job.posted_at.replace(tzinfo=None), datetime(2026, 11, 21, 9, 0))
        self.assertEqual(job.required_skills, [])
        self.assertEqual(job.min_experience, 0)
        self.assertTrue(job.is_active)
        self.assertFalse(job.is_matchable)
        self.assertEqual(job.matchability_status, "unmatchable")
        self.assertIn("not supplied", job.matchability_reason)
        self.assertTrue(job.description_is_snippet)
        self.assertFalse(job.requirements_available)

    def test_importing_the_same_listing_twice_updates_one_row(self):
        self._import(search_for(listing()), commit=True)
        first_id = self.session.scalar(select(Job.id))
        revised = listing(title="Senior Python Developer", description="Lead Python services.")

        summary = self._import(search_for(revised), commit=True)

        jobs = list(self.session.scalars(select(Job)))
        self.assertEqual(summary.inserted, 0)
        self.assertEqual(summary.updated, 1)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].id, first_id)
        self.assertEqual(jobs[0].title, "Senior Python Developer")
        self.assertEqual(jobs[0].description, "Lead Python services.")

    def test_duplicate_provider_ids_are_rejected_by_the_database(self):
        self.session.add(_external())
        self.session.commit()
        self.session.add(_external())

        with self.assertRaises(IntegrityError):
            self.session.commit()

    def test_manual_jobs_and_saved_links_stay_in_place(self):
        manual = Job(
            title="Python Developer",
            company="BrightStack",
            location="Bengaluru",
            description="Sample listing",
            required_skills=["Python", "FastAPI"],
            min_experience=2,
        )
        external = _external(required_skills=["SQL"], min_experience=4)
        candidate = Candidate(
            name="Import Test",
            email="import-test@example.com",
            skills=["Python"],
            preferred_roles=["Developer"],
            preferred_locations=["London"],
            years_experience=1,
        )
        self.session.add_all([manual, external, candidate])
        self.session.commit()
        self.session.add_all(
            [
                SavedJob(candidate_id=candidate.id, job_id=manual.id),
                SavedJob(candidate_id=candidate.id, job_id=external.id),
            ]
        )
        self.session.commit()
        manual_id = manual.id
        external_id = external.id

        self._import(search_for(listing(title="Updated Python Developer")), commit=True)

        stored_manual = self.session.get(Job, manual_id)
        stored_external = self.session.get(Job, external_id)
        saved = list(self.session.scalars(select(SavedJob).order_by(SavedJob.job_id)))
        self.assertEqual(stored_manual.title, "Python Developer")
        self.assertEqual(stored_manual.company, "BrightStack")
        self.assertEqual(stored_manual.required_skills, ["Python", "FastAPI"])
        self.assertEqual(stored_manual.min_experience, 2)
        self.assertIsNone(stored_manual.source)
        self.assertTrue(stored_manual.is_matchable)
        self.assertTrue(stored_manual.requirements_available)
        self.assertFalse(stored_external.is_matchable)
        self.assertEqual(stored_external.title, "Updated Python Developer")
        self.assertEqual(stored_external.required_skills, ["SQL"])
        self.assertEqual(stored_external.min_experience, 4)
        self.assertEqual([row.job_id for row in saved], [manual_id, external_id])
        self.assertEqual(self.session.scalar(select(func.count()).select_from(Job)), 2)

    def test_missing_optional_provider_fields_stay_empty(self):
        item = listing(description=None, created=None, redirect_url=None)
        self._import(search_for(item), commit=True)

        job = self.session.scalar(select(Job))
        self.assertIsNone(job.description)
        self.assertIsNone(job.posted_at)
        self.assertIsNone(job.source_url)
        self.assertEqual(job.required_skills, [])
        self.assertEqual(job.min_experience, 0)

    def test_incomplete_rows_are_skipped(self):
        summary = self._import(
            search_for(listing(external_id=""), listing(company=""), listing()),
            commit=True,
        )

        self.assertEqual(summary.skipped, 2)
        self.assertEqual(summary.inserted, 1)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(Job)), 1)

    def test_dry_run_does_not_write_jobs_or_logs(self):
        self.session.add(_manual())
        self.session.commit()

        summary = self._import(search_for(listing()), commit=False)

        self.assertEqual(summary.ready, 1)
        self.assertEqual(summary.inserted, 1)
        self.assertFalse(summary.wrote)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(Job)), 1)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(JobSyncLog)), 0)
        self.assertIsNone(self.session.scalar(select(Job).where(Job.source == "adzuna")))

    def test_failed_request_does_not_change_stored_jobs(self):
        self.session.add(_manual())
        self.session.commit()
        before = self.session.scalar(select(Job.title))

        summary = self._import(search_for(error=AdzunaError("The Adzuna request timed out.")), commit=True)

        self.assertEqual(summary.status, "error")
        self.assertEqual(self.session.scalar(select(Job.title)), before)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(Job)), 1)
        self.assertTrue(self.session.scalar(select(Job.is_active)))

    def test_successful_import_writes_a_sync_log(self):
        summary = self._import(search_for(listing(), listing(external_id="200", title="Second Role")), commit=True)

        log = self.session.scalar(select(JobSyncLog))
        self.assertEqual(summary.fetched, 2)
        self.assertEqual(log.provider, "adzuna")
        self.assertEqual(log.country, "gb")
        self.assertEqual(log.search_query, "Python Developer")
        self.assertEqual(log.fetched_count, 2)
        self.assertEqual(log.inserted_count, 2)
        self.assertEqual(log.updated_count, 0)
        self.assertEqual(log.skipped_count, 0)
        self.assertEqual(log.status, "success")
        self.assertIsNone(log.error_message)
        self.assertIsNotNone(log.started_at)
        self.assertIsNotNone(log.completed_at)

    def test_unexpected_errors_are_stored_without_credentials(self):
        self.session.add(_manual())
        self.session.commit()

        def search(**_kwargs):
            raise RuntimeError(f"app_key={SECRET}")

        with patch("services.job_import.get_adzuna_app_key", return_value=SECRET):
            summary = self._import(search, commit=True)

        log = self.session.scalar(select(JobSyncLog))
        self.assertEqual(summary.error_message, "The Adzuna request could not be completed.")
        self.assertEqual(log.error_message, "The Adzuna request could not be completed.")
        self.assertNotIn(SECRET, log.error_message)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(Job)), 1)

    def test_schema_statements_only_add_columns_and_an_index(self):
        sql = "\n".join(JOB_SOURCE_STATEMENTS).lower()
        self.assertIn("add column if not exists source", sql)
        self.assertIn("add column if not exists external_job_id", sql)
        self.assertIn("add column if not exists is_matchable", sql)
        self.assertIn("add column if not exists requirements_available", sql)
        self.assertIn("add column if not exists description_is_snippet", sql)
        self.assertIn("if not exists", sql)
        self.assertIn("uq_jobs_source_listing", sql)
        self.assertNotIn("drop table", sql)
        self.assertNotIn("drop constraint", sql)
        self.assertNotIn("saved_jobs", sql)
        self.assertNotIn("delete from", sql)
        self.assertNotIn("truncate", sql)

    def _import(self, search, commit: bool):
        summary = import_adzuna_jobs(
            country="gb",
            what="Python Developer",
            limit=5,
            commit=commit,
            session=self.session,
            search=search,
            now=lambda: WHEN,
        )
        self.session.expire_all()
        return summary


def _manual() -> Job:
    return Job(
        title="Python Developer",
        company="BrightStack",
        location="Bengaluru",
        description="Sample listing",
        required_skills=["Python"],
        min_experience=2,
    )


def _external(**overrides) -> Job:
    values = {
        "title": "Python Developer",
        "company": "Northwind",
        "location": "London",
        "description": "Build Python services.",
        "required_skills": [],
        "min_experience": 0,
        "source": "adzuna",
        "external_job_id": "100",
        "source_country": "gb",
        "is_active": True,
    }
    values.update(overrides)
    return Job(**values)


class CatalogueImportTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        self.session = sessionmaker(bind=engine)()

    def tearDown(self):
        self.session.close()

    def test_dry_run_classifies_new_and_existing_rows_without_writing(self):
        self.session.add(_external())
        self.session.commit()
        summary = _catalogue(
            _found("100", title="Senior Python Developer"),
            _found("200", title="Data Analyst", queries=("Data Analyst",)),
            attempts=(
                _attempt("Python Developer", fetched=2),
                _attempt("Data Analyst", fetched=1),
            ),
            cross_query=1,
        )

        plan = import_catalogue(
            summary,
            session=self.session,
            commit=False,
            known_keys={("adzuna", "gb", "100")},
            now=lambda: WHEN,
        )

        self.assertEqual(plan.insertable, 1)
        self.assertEqual(plan.updated, 1)
        self.assertEqual(plan.unmatchable, 2)
        self.assertEqual(plan.duplicates_skipped, 1)
        self.assertFalse(plan.wrote)
        self.assertFalse(plan.logs_written)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(Job)), 1)
        self.assertEqual(self.session.scalar(select(Job.title)), "Python Developer")
        self.assertEqual(self.session.scalar(select(func.count()).select_from(JobSyncLog)), 0)

    def test_commit_inserts_both_countries_and_a_second_run_updates(self):
        summary = _catalogue(
            _found("100"),
            _found("100", country="in", location="Bengaluru", source_url="https://www.adzuna.in/details/100"),
        )

        first = import_catalogue(summary, session=self.session, commit=True, now=lambda: WHEN)
        self.session.expire_all()
        second = import_catalogue(summary, session=self.session, commit=True, now=lambda: WHEN)
        self.session.expire_all()

        rows = list(self.session.scalars(select(Job).order_by(Job.source_country)))
        self.assertEqual(first.insertable, 2)
        self.assertEqual(first.updated, 0)
        self.assertTrue(first.wrote)
        self.assertEqual(second.insertable, 0)
        self.assertEqual(second.updated, 2)
        self.assertEqual(len(rows), 2)
        self.assertEqual({row.source_country for row in rows}, {"gb", "in"})
        self.assertTrue(all(row.is_matchable is False and row.requirements_available is False for row in rows))
        self.assertEqual(self.session.scalar(select(func.count()).select_from(JobSyncLog)), 2)

    def test_manual_jobs_saved_links_and_absent_listings_stay_untouched(self):
        manual = _manual()
        absent = _external(external_job_id="999", title="Keep Active", source_country="in")
        candidate = Candidate(
            name="Import Test",
            email="catalogue@example.com",
            skills=["Python"],
            preferred_roles=["Developer"],
            preferred_locations=["London"],
            years_experience=1,
        )
        self.session.add_all([manual, absent, candidate])
        self.session.commit()
        self.session.add(SavedJob(candidate_id=candidate.id, job_id=manual.id))
        self.session.commit()
        summary = _catalogue(
            _found("100", title="Updated Python Developer"),
            attempts=(
                _attempt("Python Developer"),
                _attempt("Java Developer", country="in", status="error", fetched=0, error="The Adzuna request timed out."),
            ),
        )

        plan = import_catalogue(summary, session=self.session, commit=True, now=lambda: WHEN)
        self.session.expire_all()

        stored_manual = self.session.scalar(select(Job).where(Job.source.is_(None)))
        stored_absent = self.session.scalar(select(Job).where(Job.external_job_id == "999"))
        logs = list(self.session.scalars(select(JobSyncLog).order_by(JobSyncLog.country, JobSyncLog.search_query)))
        self.assertEqual(plan.insertable, 1)
        self.assertEqual(stored_manual.title, "Python Developer")
        self.assertEqual(stored_manual.required_skills, ["Python"])
        self.assertTrue(stored_manual.is_matchable)
        self.assertEqual(stored_absent.title, "Keep Active")
        self.assertTrue(stored_absent.is_active)
        self.assertEqual(self.session.scalar(select(SavedJob.job_id)), manual.id)
        self.assertEqual([log.status for log in logs], ["success", "error"])
        self.assertEqual(logs[0].inserted_count, 1)
        self.assertEqual(logs[1].inserted_count, 0)
        self.assertEqual(logs[1].updated_count, 0)

    def test_a_repeated_source_id_is_stored_once(self):
        summary = _catalogue(
            _found("100", location="London"),
            _found("100", location="Bristol", source_url="https://www.adzuna.co.uk/jobs/land/ad/100-other"),
        )

        plan = import_catalogue(summary, session=self.session, commit=True, now=lambda: WHEN)
        self.session.expire_all()

        self.assertEqual(plan.insertable, 1)
        self.assertEqual(plan.identity_conflicts, 1)
        self.assertEqual(plan.duplicates_skipped, 1)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(Job)), 1)
        self.assertEqual(self.session.scalar(select(Job.location)), "London")

    def test_a_failed_write_keeps_no_success_log_and_no_new_job(self):
        self.session.add(_manual())
        self.session.commit()
        original = self.session.commit

        def fail_once():
            self.session.commit = original
            raise RuntimeError("could not store the rows")

        self.session.commit = fail_once
        plan = import_catalogue(
            _catalogue(_found("100")),
            session=self.session,
            commit=True,
            now=lambda: WHEN,
        )
        self.session.expire_all()

        logs = list(self.session.scalars(select(JobSyncLog)))
        self.assertFalse(plan.wrote)
        self.assertEqual(plan.error_message, "The Adzuna request could not be completed.")
        self.assertEqual(self.session.scalar(select(func.count()).select_from(Job)), 1)
        self.assertIsNone(self.session.scalar(select(Job).where(Job.source == "adzuna")))
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].status, "error")
        self.assertEqual(logs[0].inserted_count, 0)
        self.assertEqual(logs[0].updated_count, 0)
        self.assertIn("rolled back", logs[0].error_message)


def _attempt(query, country="gb", status="success", fetched=1, error=None):
    return SearchAttempt(
        country,
        query,
        "Software development",
        status,
        200 if status == "success" else 503,
        fetched,
        error,
    )


def _found(external_id, **overrides) -> DiscoveredJob:
    values = {
        "source": "adzuna",
        "external_job_id": external_id,
        "country": "gb",
        "title": "Python Developer",
        "company": "Northwind",
        "location": "London",
        "description": "Build Python services.",
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
        "queries": ("Python Developer",),
        "categories": ("Software development",),
    }
    values.update(overrides)
    return DiscoveredJob(**values)


def _catalogue(*jobs, attempts=None, cross_query=0) -> DiscoverySummary:
    rows = tuple(jobs)
    searches = attempts or (_attempt("Python Developer", fetched=len(rows)),)
    by_country = {}
    for job in rows:
        by_country[job.country] = by_country.get(job.country, 0) + 1
    succeeded = tuple(dict.fromkeys(item.country for item in searches if item.status == "success"))
    failed = tuple(dict.fromkeys(item.country for item in searches if item.country not in succeeded))
    return DiscoverySummary(
        attempts=tuple(searches),
        jobs=rows,
        requests_attempted=len(searches),
        requests_succeeded=sum(item.status == "success" for item in searches),
        requests_failed=sum(item.status == "error" for item in searches),
        countries_succeeded=succeeded,
        countries_failed=failed,
        fetched=sum(item.fetched for item in searches),
        unique=len(rows),
        cross_query_duplicates=cross_query,
        kept_separate=0,
        by_country=by_country,
        by_category={},
        missing_required_skills=len(rows),
        incomplete_descriptions=len(rows),
        missing_descriptions=0,
        old_listings=0,
        undated_listings=0,
    )


if __name__ == "__main__":
    unittest.main()
