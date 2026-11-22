"""Checks for Gemini explanations. The real API and the real key are not used."""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.ai_service import build_prompt, explain_matches
from services.matching import MatchScore


def candidate():
    return SimpleNamespace(
        name="Asha Rao",
        email="asha@example.com",
        education="B.Tech",
        skills=["Python", "SQL"],
        preferred_roles=["Software Engineer"],
        preferred_locations=["Bengaluru"],
        years_experience=1,
    )


def job():
    return SimpleNamespace(
        title="Data Analyst",
        company="Northwind",
        location="Bengaluru",
        description="SQL and Python reporting.",
        required_skills=["Python", "SQL"],
    )


def score():
    return MatchScore(
        total_score=80.0,
        skill_score=70.0,
        role_score=0.0,
        location_score=10.0,
        matched_skills=["Python", "SQL"],
        missing_skills=[],
    )


class ExplodingModels:
    def generate_content(self, **kwargs):
        raise AssertionError("Gemini should not be called")


class ExplodingClient:
    def __init__(self):
        self.models = ExplodingModels()


class FakeModels:
    def __init__(self, text="The skills line up. The location also matches.", error=None):
        self.text = text
        self.error = error
        self.calls = []

    def generate_content(self, *, model, contents):
        self.calls.append({"model": model, "contents": contents})
        if self.error is not None:
            raise self.error
        return SimpleNamespace(text=self.text)


class FakeClient:
    def __init__(self, models):
        self.models = models


class ExplanationTests(unittest.TestCase):
    def test_missing_key_uses_fallback_and_does_not_call_gemini(self):
        with patch("services.ai_service.get_gemini_api_key", return_value=""):
            explanations = explain_matches(candidate(), [(job(), score())], client=ExplodingClient())

        self.assertEqual(len(explanations), 1)
        self.assertIn("80.0 out of 100", explanations[0])
        self.assertIn("Python, SQL", explanations[0])

    def test_api_error_uses_fallback_without_the_error_text(self):
        models = FakeModels(error=RuntimeError("service unavailable"))
        with patch("services.ai_service.get_gemini_api_key", return_value="test-key"):
            explanations = explain_matches(candidate(), [(job(), score())], client=FakeClient(models))

        self.assertIn("80.0 out of 100", explanations[0])
        self.assertNotIn("service unavailable", explanations[0])

    def test_prompt_contains_the_score_and_omits_personal_identifiers(self):
        prompt = build_prompt(candidate(), [(job(), score())])

        self.assertIn("Total score: 80.0 out of 100", prompt)
        self.assertIn("Skill score: 70.0 out of 70", prompt)
        self.assertNotIn("asha@example.com", prompt)
        self.assertNotIn("Asha Rao", prompt)

    def test_model_name_comes_from_configuration(self):
        models = FakeModels()
        with (
            patch("services.ai_service.get_gemini_api_key", return_value="test-key"),
            patch("services.ai_service.get_gemini_model", return_value="gemini-3.8-flash"),
        ):
            explanations = explain_matches(candidate(), [(job(), score())], client=FakeClient(models))

        self.assertEqual(models.calls[0]["model"], "gemini-3.8-flash")
        self.assertEqual(explanations, ["The skills line up. The location also matches."])

    def test_blank_model_setting_defaults_to_gemini_3_8_flash(self):
        from settings import get_gemini_model

        with patch.dict("os.environ", {"GEMINI_MODEL": ""}, clear=False):
            self.assertEqual(get_gemini_model(), "gemini-3.8-flash")

    def test_custom_model_setting_is_used(self):
        from settings import get_gemini_model

        with patch.dict("os.environ", {"GEMINI_MODEL": "gemini-2.5-flash"}, clear=False):
            self.assertEqual(get_gemini_model(), "gemini-2.5-flash")

    def test_failure_log_redacts_secrets(self):
        models = FakeModels(error=RuntimeError("bad key test-key Authorization: Bearer test-key"))
        with (
            patch("services.ai_service.get_gemini_api_key", return_value="test-key"),
            self.assertLogs("services.ai_service", level="WARNING") as captured,
        ):
            explanations = explain_matches(candidate(), [(job(), score())], client=FakeClient(models))

        logged = "\n".join(captured.output)
        self.assertIn("RuntimeError", logged)
        self.assertNotIn("test-key", logged)
        self.assertIn("[REDACTED]", logged)
        self.assertIn("80.0 out of 100", explanations[0])


if __name__ == "__main__":
    unittest.main()
