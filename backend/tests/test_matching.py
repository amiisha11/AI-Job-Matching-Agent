"""Checks for the job score. These tests do not open the database."""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.matching import eligible_for_ranking, score_job


def profile(**kwargs):
    defaults = {
        "skills": [],
        "preferred_roles": [],
        "preferred_locations": [],
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def listing(**kwargs):
    defaults = {
        "id": 1,
        "title": "",
        "location": "",
        "required_skills": [],
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class MatchScoreTests(unittest.TestCase):
    def test_asha_rao_and_northwind_data_analyst(self):
        candidate = profile(
            skills=["Python", "SQL", "FastAPI"],
            preferred_roles=["Software Engineer"],
            preferred_locations=["Bengaluru"],
        )
        job = listing(
            title="Data Analyst",
            location="Bengaluru",
            required_skills=["Python", "SQL"],
        )

        score = score_job(candidate, job)

        self.assertEqual(score.skill_score, 70.0)
        self.assertEqual(score.role_score, 0.0)
        self.assertEqual(score.location_score, 10.0)
        self.assertEqual(score.total_score, 80.0)
        self.assertEqual(score.matched_skills, ["Python", "SQL"])
        self.assertEqual(score.missing_skills, [])

    def test_skill_comparison_ignores_case_and_space(self):
        score = score_job(
            profile(skills=[" python ", "sql"]),
            listing(required_skills=["Python", "SQL", "Tableau"]),
        )

        self.assertEqual(score.skill_score, 46.67)
        self.assertEqual(score.matched_skills, ["Python", "SQL"])
        self.assertEqual(score.missing_skills, ["Tableau"])

    def test_empty_required_skills_award_zero_without_error(self):
        score = score_job(profile(skills=["Python"]), listing(required_skills=[]))

        self.assertEqual(score.skill_score, 0.0)
        self.assertEqual(score.matched_skills, [])
        self.assertEqual(score.missing_skills, [])

    def test_role_and_location_are_case_insensitive(self):
        score = score_job(
            profile(
                preferred_roles=["data analyst"],
                preferred_locations=[" bengaluru "],
            ),
            listing(title="Junior Data Analyst", location="Bengaluru"),
        )

        self.assertEqual(score.role_score, 20.0)
        self.assertEqual(score.location_score, 10.0)
        self.assertEqual(score.total_score, 30.0)

    def test_seeded_jobs_with_skills_stay_rankable_and_keep_the_formula(self):
        job = listing(
            title="Data Analyst",
            location="Bengaluru",
            required_skills=["Python", "SQL"],
            is_matchable=True,
            requirements_available=True,
            matchability_status="matchable",
        )
        candidate = profile(
            skills=["Python", "SQL"],
            preferred_roles=["Data Analyst"],
            preferred_locations=["Bengaluru"],
        )

        self.assertTrue(eligible_for_ranking(job))
        score = score_job(candidate, job)
        self.assertEqual(score.skill_score, 70.0)
        self.assertEqual(score.role_score, 20.0)
        self.assertEqual(score.location_score, 10.0)
        self.assertEqual(score.total_score, 100.0)

    def test_external_jobs_without_requirements_are_not_ranked(self):
        job = listing(
            title="Python Developer",
            location="London",
            required_skills=[],
            is_matchable=False,
            requirements_available=False,
            matchability_status="unmatchable",
            matchability_reason="Required skills were not supplied by the provider.",
        )

        self.assertFalse(eligible_for_ranking(job))
        score = score_job(
            profile(skills=["Python"], preferred_roles=["Python Developer"], preferred_locations=["London"]),
            job,
        )
        self.assertEqual(score.skill_score, 0.0)
        self.assertNotEqual(score.total_score, 100.0)

    def test_unrelated_role_and_location_score_zero(self):
        score = score_job(
            profile(preferred_roles=["Designer"], preferred_locations=["Mumbai"]),
            listing(title="Data Analyst", location="Bengaluru"),
        )

        self.assertEqual(score.role_score, 0.0)
        self.assertEqual(score.location_score, 0.0)


if __name__ == "__main__":
    unittest.main()
