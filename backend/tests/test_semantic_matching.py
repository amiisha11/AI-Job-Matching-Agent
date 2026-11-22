"""Semantic skill pairing. These tests use fake vectors and do not call Gemini."""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.ai_service import embed_skill_strings
from services.matching import maximum_weight_assignment, score_job, score_with_skill_vectors, skill_texts_for_embedding


def profile(**kwargs):
    defaults = {"skills": [], "preferred_roles": [], "preferred_locations": [], "name": "Asha Rao", "email": "asha@example.com"}
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def listing(**kwargs):
    defaults = {"required_skills": [], "title": "Data Analyst", "location": "Mumbai", "company": "Example"}
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class ExactAndFallbackTests(unittest.TestCase):
    def test_exact_match_receives_full_credit(self):
        score = score_with_skill_vectors(
            profile(skills=["Python", "SQL"]),
            listing(required_skills=["Python", "SQL"]),
            vectors={"python": [1.0, 0.0], "sql": [0.0, 1.0]},
        )

        self.assertEqual(score.skill_score, 70.0)
        self.assertEqual(score.matched_skills, ["Python", "SQL"])
        self.assertEqual(score.semantic_matches, [])
        self.assertEqual(score.missing_skills, [])

    def test_duplicate_skills_are_counted_once(self):
        score = score_with_skill_vectors(
            profile(skills=["Python", " python "]),
            listing(required_skills=["Python", "Python", "SQL"]),
            vectors=None,
        )

        self.assertEqual(score.matched_skills, ["Python"])
        self.assertEqual(score.missing_skills, ["SQL"])
        self.assertEqual(score.skill_score, 35.0)

    def test_missing_embedding_uses_exact_score(self):
        candidate = profile(skills=["Python"])
        job = listing(required_skills=["Python", "Tableau"])

        self.assertEqual(score_with_skill_vectors(candidate, job, None), score_job(candidate, job))


class SemanticCreditTests(unittest.TestCase):
    def test_related_skill_receives_cosine_credit(self):
        score = score_with_skill_vectors(
            profile(skills=["Postgres"]),
            listing(required_skills=["PostgreSQL"]),
            vectors={"postgres": [1.0, 0.0], "postgresql": [0.8, 0.6]},
            threshold=0.75,
        )

        self.assertEqual(score.matched_skills, [])
        self.assertEqual(score.missing_skills, [])
        self.assertEqual(len(score.semantic_matches), 1)
        self.assertEqual(score.semantic_matches[0].required_skill, "PostgreSQL")
        self.assertEqual(score.semantic_matches[0].candidate_skill, "Postgres")
        self.assertEqual(score.semantic_matches[0].similarity, 0.8)
        self.assertEqual(score.skill_score, 56.0)

    def test_similarity_below_threshold_is_missing(self):
        score = score_with_skill_vectors(
            profile(skills=["Design"]),
            listing(required_skills=["PostgreSQL"]),
            vectors={"design": [1.0, 0.0], "postgresql": [0.6, 0.8]},
            threshold=0.75,
        )

        self.assertEqual(score.semantic_matches, [])
        self.assertEqual(score.missing_skills, ["PostgreSQL"])
        self.assertEqual(score.skill_score, 0.0)

    def test_exact_match_consumes_the_candidate_skill(self):
        score = score_with_skill_vectors(
            profile(skills=["Python"]),
            listing(required_skills=["Python", "Python programming"]),
            vectors={"python": [1.0, 0.0], "python programming": [1.0, 0.0]},
            threshold=0.75,
        )

        self.assertEqual(score.matched_skills, ["Python"])
        self.assertEqual(score.semantic_matches, [])
        self.assertEqual(score.missing_skills, ["Python programming"])
        self.assertEqual(score.skill_score, 35.0)


class OptimalPairingTests(unittest.TestCase):
    def test_assignment_maximizes_total_weight(self):
        weights = [
            [0.99, 0.80],
            [0.90, 0.10],
        ]

        pairs = maximum_weight_assignment(weights)

        self.assertEqual(sorted(pairs), [(0, 1), (1, 0)])

    def test_reversed_skill_order_selects_the_same_pairs(self):
        forward = maximum_weight_assignment(
            [
                [0.99, 0.80],
                [0.90, 0.10],
            ]
        )
        reversed_order = maximum_weight_assignment(
            [
                [0.10, 0.90],
                [0.80, 0.99],
            ]
        )

        self.assertEqual(sorted(forward), [(0, 1), (1, 0)])
        self.assertEqual(sorted(reversed_order), [(0, 1), (1, 0)])

    def test_two_related_skills_are_both_credited(self):
        score = score_with_skill_vectors(
            profile(skills=["Postgres", "JS"]),
            listing(required_skills=["PostgreSQL", "JavaScript"]),
            vectors={
                "postgres": [1.0, 0.0, 0.0],
                "postgresql": [0.8, 0.6, 0.0],
                "js": [0.0, 0.6, 0.8],
                "javascript": [0.0, 0.0, 1.0],
            },
            threshold=0.75,
        )

        pairs = {(item.required_skill, item.candidate_skill) for item in score.semantic_matches}
        self.assertEqual(pairs, {("PostgreSQL", "Postgres"), ("JavaScript", "JS")})
        self.assertEqual(score.missing_skills, [])
        self.assertEqual(score.skill_score, 56.0)


class EmbeddingFallbackTests(unittest.TestCase):
    def test_embedding_text_contains_skills_only(self):
        texts = skill_texts_for_embedding(
            profile(skills=["Python"]),
            [listing(required_skills=["SQL"])],
        )

        self.assertEqual(texts, ["Python", "SQL"])
        self.assertNotIn("asha@example.com", texts)
        self.assertNotIn("Asha Rao", texts)

    def test_embedding_failure_returns_no_vectors(self):
        class ExplodingModels:
            def embed_content(self, **kwargs):
                raise RuntimeError("service unavailable")

        class ExplodingClient:
            def __init__(self):
                self.models = ExplodingModels()

        with (
            patch("services.ai_service.get_gemini_api_key", return_value="test-key"),
            patch("services.ai_service.get_gemini_embedding_model", return_value="models/gemini-embedding-2"),
        ):
            vectors = embed_skill_strings(["Python"], client=ExplodingClient())

        self.assertIsNone(vectors)


if __name__ == "__main__":
    unittest.main()
