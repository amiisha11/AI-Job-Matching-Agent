"""Live embedding check. Synthetic skill strings only; no database access."""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from google import genai

from services.ai_service import EMBEDDING_DIMENSIONS, embed_skill_strings
from services.matching import cosine_similarity, score_with_skill_vectors
from settings import get_gemini_api_key, get_gemini_embedding_model, get_skill_similarity_threshold

CANDIDATE_SKILL = "React.js"
RELATED_SKILL = "React"
UNRELATED_SKILL = "Tax Law"


class RecordingModels:
    """Record the embedding request, then call the real Gemini client."""

    def __init__(self, inner):
        self.inner = inner
        self.calls = []

    def embed_content(self, **kwargs):
        self.calls.append(
            {
                "model": kwargs.get("model"),
                "contents": kwargs.get("contents"),
                "config": kwargs.get("config"),
            }
        )
        return self.inner.embed_content(**kwargs)


class RecordingClient:
    def __init__(self, inner):
        self.inner = inner
        self.models = RecordingModels(inner.models)


def profile(skills):
    return SimpleNamespace(skills=skills, preferred_roles=[], preferred_locations=[])


def listing(required_skills):
    return SimpleNamespace(required_skills=required_skills, title="Example", location="Nowhere")


class LiveEmbeddingTests(unittest.TestCase):
    def test_live_embeddings_score_related_and_unrelated_skills(self):
        api_key = get_gemini_api_key()
        self.assertTrue(api_key, "GEMINI_API_KEY is missing, so live embeddings cannot be checked.")
        configured_model = get_gemini_embedding_model()
        threshold = get_skill_similarity_threshold()

        recorder = RecordingClient(genai.Client(api_key=api_key))
        vectors = embed_skill_strings(
            [CANDIDATE_SKILL, RELATED_SKILL, UNRELATED_SKILL],
            client=recorder,
        )

        self.assertIsNotNone(vectors, "The live embedding call returned no vectors.")
        self.assertEqual(len(recorder.models.calls), 1)
        call = recorder.models.calls[0]
        self.assertEqual(call["model"], configured_model)
        self.assertEqual(call["model"], "models/gemini-embedding-2")
        sent_texts = [
            part.text
            for content in call["contents"]
            for part in content.parts
        ]
        self.assertEqual(sent_texts, [CANDIDATE_SKILL, RELATED_SKILL, UNRELATED_SKILL])
        self.assertEqual(len(call["contents"]), 3)
        self.assertEqual(call["config"], {"output_dimensionality": EMBEDDING_DIMENSIONS})
        self.assertEqual(set(vectors), {"react.js", "react", "tax law"})
        for values in vectors.values():
            self.assertEqual(len(values), EMBEDDING_DIMENSIONS)
            self.assertTrue(all(isinstance(value, (int, float)) for value in values))

        related_similarity = cosine_similarity(vectors["react.js"], vectors["react"])
        unrelated_similarity = cosine_similarity(vectors["react.js"], vectors["tax law"])
        print(
            f"React.js-React cosine={related_similarity:.6f}; "
            f"React.js-Tax Law cosine={unrelated_similarity:.6f}; "
            f"threshold={threshold}"
        )

        related_score = score_with_skill_vectors(
            profile([CANDIDATE_SKILL]),
            listing([RELATED_SKILL]),
            vectors,
            threshold,
        )
        self.assertGreaterEqual(
            related_similarity,
            threshold,
            f"React.js-React cosine {related_similarity:.6f} is below the configured threshold {threshold}.",
        )
        self.assertEqual(related_score.matched_skills, [])
        self.assertEqual(related_score.missing_skills, [])
        self.assertEqual(len(related_score.semantic_matches), 1)
        match = related_score.semantic_matches[0]
        self.assertEqual(match.required_skill, RELATED_SKILL)
        self.assertEqual(match.candidate_skill, CANDIDATE_SKILL)
        self.assertGreaterEqual(match.similarity, threshold)
        self.assertEqual(related_score.skill_score, round(70 * match.similarity, 2))

        unrelated_score = score_with_skill_vectors(
            profile([CANDIDATE_SKILL]),
            listing([UNRELATED_SKILL]),
            vectors,
            threshold,
        )
        self.assertLess(
            unrelated_similarity,
            threshold,
            f"React.js-Tax Law cosine {unrelated_similarity:.6f} is not below the configured threshold {threshold}.",
        )
        self.assertEqual(unrelated_score.semantic_matches, [])
        self.assertEqual(unrelated_score.missing_skills, [UNRELATED_SKILL])
        self.assertEqual(unrelated_score.skill_score, 0.0)


if __name__ == "__main__":
    unittest.main()
