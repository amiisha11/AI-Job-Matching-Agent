"""Stored provider categories stay on the job API. They do not change match scores."""

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models import Base, Candidate, Job, SavedJob
from routes.jobs import JobRead, SavedJobRead
from services.job_filters import build_filter_metadata, filter_jobs, search_from_params
from services.matching import eligible_for_ranking, score_job


def _job(**overrides) -> dict:
    row = {
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
    row.update(overrides)
    return row


class CategoryMappingTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine, tables=[Candidate.__table__, Job.__table__, SavedJob.__table__])
        self.session = sessionmaker(bind=engine)()

    def tearDown(self):
        self.session.close()

    def test_nullable_category_columns_round_trip_without_replacing_a_blank(self):
        columns = {column.name: column for column in Job.__table__.columns}
        self.assertTrue(columns["category_label"].nullable)
        self.assertTrue(columns["category_tag"].nullable)
        self.assertEqual(columns["category_label"].type.length, 200)
        self.assertEqual(columns["category_tag"].type.length, 80)

        labelled = Job(
            title="Nurse",
            company="Hospital",
            location="York",
            required_skills=[],
            min_experience=0,
            category_label="Healthcare & Nursing Jobs",
            category_tag="healthcare-nursing-jobs",
            is_matchable=False,
            requirements_available=False,
        )
        blank = Job(title="Analyst", company="Northwind", location="Pune", required_skills=["Excel"], min_experience=1)
        self.session.add_all([labelled, blank])
        self.session.commit()
        self.session.expire_all()

        stored = {row.title: row for row in self.session.query(Job).all()}
        self.assertEqual(stored["Nurse"].category_label, "Healthcare & Nursing Jobs")
        self.assertEqual(stored["Nurse"].category_tag, "healthcare-nursing-jobs")
        self.assertIsNone(stored["Analyst"].category_label)
        self.assertIsNone(stored["Analyst"].category_tag)

    def test_list_detail_and_saved_job_responses_include_the_stored_category(self):
        candidate = Candidate(
            name="Ada Lovelace",
            email="ada@example.com",
            skills=["Python"],
            preferred_roles=[],
            preferred_locations=[],
        )
        job = Job(
            title="Python Developer",
            company="Northwind",
            location="London",
            required_skills=["Python"],
            min_experience=2,
            source="adzuna",
            source_country="gb",
            source_url="https://www.adzuna.co.uk/jobs/land/ad/10",
            category_label="IT Jobs",
            category_tag="it-jobs",
        )
        self.session.add(candidate)
        self.session.add(job)
        self.session.flush()
        saved = SavedJob(candidate_id=candidate.id, job_id=job.id, created_at=datetime.now(timezone.utc))
        self.session.add(saved)
        self.session.commit()
        self.session.refresh(saved)

        listing = JobRead.model_validate(job).model_dump()
        detail = JobRead.model_validate(self.session.get(Job, job.id)).model_dump()
        saved_body = SavedJobRead.model_validate(saved).model_dump()

        for body in (listing, detail, saved_body["job"]):
            self.assertEqual(body["category_label"], "IT Jobs")
            self.assertEqual(body["category_tag"], "it-jobs")
            self.assertEqual(body["title"], "Python Developer")
            self.assertEqual(body["source_url"], "https://www.adzuna.co.uk/jobs/land/ad/10")


class CategoryFilterTests(unittest.TestCase):
    def test_filters_use_stored_categories_and_keep_blank_rows_separate(self):
        rows = [
            _job(id=1, category_label="IT Jobs", category_tag="it-jobs", location="London", source_country="gb"),
            _job(
                id=2,
                title="Solicitor",
                category_label="Legal Jobs",
                category_tag="legal-jobs",
                location="Mumbai",
                source_country="in",
                required_skills=["Contracts"],
            ),
            _job(id=3, title="Teacher", location="Delhi", source_country="in", category_label=None, category_tag=None),
        ]

        options = build_filter_metadata(rows, [{"tag": "sales-jobs", "label": "Sales Jobs"}])
        self.assertEqual(
            options["categories"],
            [
                {"value": "it-jobs", "label": "IT Jobs"},
                {"value": "legal-jobs", "label": "Legal Jobs"},
            ],
        )

        legal = filter_jobs(rows, search_from_params({"category": "legal-jobs"}))
        self.assertEqual([item["id"] for item in legal], [2])

        combined = filter_jobs(rows, search_from_params({"category": "it-jobs", "country": "gb", "q": "python"}))
        self.assertEqual([item["id"] for item in combined], [1])

        other_country = filter_jobs(rows, search_from_params({"category": "it-jobs", "country": "in"}))
        self.assertEqual(other_country, [])

        missing = filter_jobs(rows, search_from_params({"category": "unspecified", "q": "teacher"}))
        self.assertEqual([item["id"] for item in missing], [3])


class CategoryMatchingTests(unittest.TestCase):
    def test_a_category_does_not_change_the_score_or_make_a_job_matchable(self):
        candidate = SimpleNamespace(skills=["Python"], preferred_roles=["Developer"], preferred_locations=["London"])
        plain = SimpleNamespace(
            title="Python Developer",
            location="London",
            required_skills=["Python"],
            is_matchable=True,
            requirements_available=True,
            category_label=None,
            category_tag=None,
        )
        labelled = SimpleNamespace(
            title="Python Developer",
            location="London",
            required_skills=["Python"],
            is_matchable=True,
            requirements_available=True,
            category_label="IT Jobs",
            category_tag="it-jobs",
        )
        uncategorised = score_job(candidate, plain)
        categorised = score_job(candidate, labelled)

        self.assertEqual(categorised.total_score, uncategorised.total_score)
        self.assertEqual(categorised.skill_score, 70)
        self.assertEqual(categorised.role_score, 20)
        self.assertEqual(categorised.location_score, 10)
        self.assertEqual(categorised.total_score, 100)

        imported = SimpleNamespace(
            title="Nurse",
            location="York",
            required_skills=[],
            is_matchable=False,
            requirements_available=False,
            category_label="Healthcare & Nursing Jobs",
            category_tag="healthcare-nursing-jobs",
        )
        self.assertFalse(eligible_for_ranking(imported))


if __name__ == "__main__":
    unittest.main()
