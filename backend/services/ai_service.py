"""Explain match scores with Gemini.

This is the only module that calls the Gemini API. The score is computed
elsewhere and is only described here. A missing key or an API failure
returns a short local sentence instead of raising.
"""

import logging
import re

from google import genai

from services.matching import MatchScore
from settings import get_gemini_api_key, get_gemini_embedding_model, get_gemini_model

EMBEDDING_DIMENSIONS = 768

logger = logging.getLogger(__name__)


def explain_matches(candidate, scored_jobs, client=None) -> list[str]:
    """Return one explanation per scored job, in the same order."""
    if not scored_jobs:
        return []

    fallbacks = [fallback_explanation(job, score) for job, score in scored_jobs]
    if not get_gemini_api_key():
        return fallbacks

    try:
        active_client = client or genai.Client(api_key=get_gemini_api_key())
        response = active_client.models.generate_content(
            model=get_gemini_model(),
            contents=build_prompt(candidate, scored_jobs),
        )
        explanations = parse_explanations(getattr(response, "text", "") or "", len(scored_jobs))
    except Exception as exc:
        logger.warning(
            "Gemini explanation failed: %s: %s",
            type(exc).__name__,
            _sanitize(exc, get_gemini_api_key()),
        )
        return fallbacks

    if not explanations:
        logger.warning("Gemini returned no usable explanation for %s job(s).", len(scored_jobs))
        return fallbacks
    return explanations


def embed_skill_strings(skills: list[str], client=None) -> dict[str, list[float]] | None:
    """Embed each distinct skill once. None means the caller should use exact matching."""
    ordered: list[tuple[str, str]] = []
    seen: set[str] = set()
    for skill in skills:
        if not isinstance(skill, str):
            continue
        cleaned = skill.strip()
        key = " ".join(cleaned.casefold().split())
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append((key, cleaned))
    if not ordered:
        return {}
    if not get_gemini_api_key():
        return None

    try:
        active_client = client or genai.Client(api_key=get_gemini_api_key())
        # gemini-embedding-2 treats a list of strings as one multi-part input.
        # One Content per skill makes the batch return one vector per skill.
        response = active_client.models.embed_content(
            model=get_gemini_embedding_model(),
            contents=[
                genai.types.Content(parts=[genai.types.Part.from_text(text=display)])
                for _, display in ordered
            ],
            config={"output_dimensionality": EMBEDDING_DIMENSIONS},
        )
        embeddings = getattr(response, "embeddings", None) or []
        if len(embeddings) != len(ordered):
            raise ValueError("The embedding response did not include one vector per skill.")
        vectors: dict[str, list[float]] = {}
        for (key, _), embedding in zip(ordered, embeddings):
            values = list(getattr(embedding, "values", None) or [])
            if not values:
                raise ValueError("The embedding response included an empty vector.")
            vectors[key] = values
        return vectors
    except Exception as exc:
        logger.warning(
            "Gemini skill embeddings failed: %s: %s",
            type(exc).__name__,
            _sanitize(exc, get_gemini_api_key()),
        )
        return None


def build_prompt(candidate, scored_jobs) -> str:
    """Describe the profile and the scores without the candidate's name or email."""
    lines = [
        "You explain job matches for a student learning job search.",
        "Use only the scores provided. Do not calculate or change any score.",
        "For each job, write exactly two short sentences.",
        "Separate each job with a line that contains only ---.",
        "Do not add headings, numbers, or the candidate's name.",
        "",
        "Candidate profile:",
        f"- Education: {_text(getattr(candidate, 'education', None))}",
        f"- Skills: {_join(getattr(candidate, 'skills', None))}",
        f"- Preferred roles: {_join(getattr(candidate, 'preferred_roles', None))}",
        f"- Preferred locations: {_join(getattr(candidate, 'preferred_locations', None))}",
        f"- Years of experience: {getattr(candidate, 'years_experience', 0)}",
        "",
    ]
    for index, (job, score) in enumerate(scored_jobs, start=1):
        lines.extend(
            [
                f"Job {index}:",
                f"- Title: {_text(getattr(job, 'title', None))}",
                f"- Company: {_text(getattr(job, 'company', None))}",
                f"- Location: {_text(getattr(job, 'location', None))}",
                f"- Description: {_clip(getattr(job, 'description', None))}",
                f"- Required skills: {_join(getattr(job, 'required_skills', None))}",
                f"- Total score: {score.total_score} out of 100",
                f"- Skill score: {score.skill_score} out of 70",
                f"- Role score: {score.role_score} out of 20",
                f"- Location score: {score.location_score} out of 10",
                f"- Matched skills: {_join(score.matched_skills)}",
                f"- Missing skills: {_join(score.missing_skills)}",
                "",
            ]
        )
    return "\n".join(lines)


def parse_explanations(text: str, expected: int) -> list[str] | None:
    """Split a Gemini reply into one explanation per job."""
    if expected == 1:
        explanation = text.strip()
        return [explanation] if explanation else None

    parts = [part.strip() for part in text.split("---")]
    parts = [part for part in parts if part]
    if len(parts) != expected:
        return None
    return parts


def _sanitize(message, secret: str) -> str:
    """Remove keys and authorization material from a Gemini error."""
    text = str(message)
    if secret:
        text = text.replace(secret, "[REDACTED]")
    text = re.sub(r"(?i)(authorization\s*[:=]\s*)(?:bearer\s+)?\S+", r"\1[REDACTED]", text)
    text = re.sub(r"(?i)\bbearer\s+\S+", "Bearer [REDACTED]", text)
    text = re.sub(r"(?i)(api[_-]?key\s*[:=]\s*)\S+", r"\1[REDACTED]", text)
    return text


def fallback_explanation(job, score: MatchScore) -> str:
    """Explain the given score without calling Gemini."""
    matched = _join(score.matched_skills)
    missing = _join(score.missing_skills)
    title = _text(getattr(job, "title", None))
    company = _text(getattr(job, "company", None))
    return (
        f"{title} at {company} scores {score.total_score} out of 100: "
        f"{score.skill_score} for skills, {score.role_score} for role, and "
        f"{score.location_score} for location. "
        f"Matched skills: {matched}. Missing skills: {missing}."
    )


def _join(values) -> str:
    if not values:
        return "none"
    items = [str(value).strip() for value in values if str(value).strip()]
    return ", ".join(items) if items else "none"


def _text(value) -> str:
    if value is None:
        return "not provided"
    cleaned = str(value).strip()
    return cleaned or "not provided"


def _clip(value, limit: int = 500) -> str:
    cleaned = _text(value)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip() + "..."
