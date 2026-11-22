"""Compare resume text with one job's real skills and description.

Coverage counts exact wording only. Related skills can be compared through
the existing skill-vector helper, and only those short skill names are
eligible for embeddings. The 70/20/10 job score is not used or returned.
"""

import re
from types import SimpleNamespace

from services.matching import score_with_skill_vectors
from services.resume_health import _QUANTIFIED, section_text

COVERAGE_FORMULA = (
    "Coverage is the number of this job's required skills found by exact wording in the resume, "
    "divided by the number of required skills, then rounded to the nearest percent, with halves rounded up. "
    "Each required skill counts once. Related wording is shown separately and is not included in the percentage. "
    "This is not an applicant tracking score."
)
_STOP_WORDS = {
    "a", "an", "the", "and", "or", "for", "with", "from", "that", "this", "your", "you",
    "our", "their", "into", "over", "under", "using", "use", "used", "will", "can", "are",
    "was", "were", "been", "have", "has", "had", "not", "but", "per", "via", "such", "than",
    "then", "they", "them", "its", "job", "role", "team", "work", "working", "including",
    "include", "across", "within", "ability", "strong", "experience", "years", "year",
    "looking", "responsibilities", "requirements", "required", "preferred", "about",
    "other", "more", "must", "should", "able", "well", "who", "what", "when", "where",
    "which", "while", "based",
}


def nearest_percent(part: int, whole: int) -> int | None:
    """Round part / whole to a percent. Halves round up."""
    if whole <= 0:
        return None
    return (100 * part + whole // 2) // whole


def match_resume_to_job(text: str, job, embedder=None, threshold: float = 0.75) -> dict:
    """Return coverage for one job. Embeddings receive skill names only."""
    source = text if isinstance(text, str) else ""
    required = _unique(getattr(job, "required_skills", None))
    found = [skill for skill in required if skill_in_text(skill, source)]
    missing = [skill for skill in required if skill not in found]
    labels = skill_labels(section_text(source, "skills"))
    related: list[dict] = []
    semantic_used = False
    if missing and labels and embedder is not None:
        vectors = embedder(_embedding_inputs(labels, missing))
        if vectors:
            semantic_used = True
            related = _related(missing, labels, vectors, threshold)
    keywords = _keywords(getattr(job, "description", None))
    keywords_found = [word for word in keywords if skill_in_text(word, source)]
    keywords_missing = [word for word in keywords if word not in keywords_found]
    return {
        "job_id": getattr(job, "id", None),
        "title": getattr(job, "title", "") or "",
        "company": getattr(job, "company", "") or "",
        "location": getattr(job, "location", "") or "",
        "min_experience": getattr(job, "min_experience", None),
        "required_count": len(required),
        "found_count": len(found),
        "coverage_percent": nearest_percent(len(found), len(required)),
        "formula": COVERAGE_FORMULA,
        "found_skills": found,
        "related_skills": related,
        "missing_skills": missing,
        "keywords_found": keywords_found,
        "keywords_missing": keywords_missing,
        "strengths": _strengths(source, found),
        "gaps": _gaps(missing, related, keywords_missing),
        "suggestions": _suggestions(source, found, missing),
        "semantic_used": semantic_used,
    }


def skill_in_text(skill: str, text: str) -> bool:
    """True when the skill phrase appears on its own, ignoring case and extra space."""
    needle = _normalize(skill)
    if not needle:
        return False
    pattern = r"(?<![a-z0-9])" + re.escape(needle) + r"(?![a-z0-9])"
    return re.search(pattern, _normalize(text)) is not None


def skill_labels(section: str) -> list[str]:
    """Short skill names from a skills section. Contact details are rejected."""
    labels: list[str] = []
    seen: set[str] = set()
    for part in re.split(r"[\n,;|/•·]+", section or ""):
        token = " ".join(part.split())
        key = _normalize(token)
        if not key or key in seen or not _safe_skill_token(token):
            continue
        seen.add(key)
        labels.append(token)
        if len(labels) == 40:
            break
    return labels


def _embedding_inputs(labels: list[str], missing: list[str]) -> list[str]:
    inputs: list[str] = []
    seen: set[str] = set()
    for value in [*labels, *missing]:
        key = _normalize(value)
        if key and key not in seen and _safe_skill_token(value):
            seen.add(key)
            inputs.append(value)
    return inputs


def _safe_skill_token(token: str) -> bool:
    if not token or len(token) > 40 or len(token.split()) > 4:
        return False
    if "@" in token or "http://" in token.casefold() or "https://" in token.casefold():
        return False
    if re.search(r"\d{3}\D*\d{4}", token):
        return False
    letters = sum(character.isalpha() for character in token)
    return letters >= 2


def _related(missing: list[str], labels: list[str], vectors, threshold: float) -> list[dict]:
    candidate = SimpleNamespace(skills=labels, preferred_roles=[], preferred_locations=[])
    compared = SimpleNamespace(title="", location="", required_skills=missing)
    scored = score_with_skill_vectors(candidate, compared, vectors, threshold)
    return [
        {
            "required_skill": item.required_skill,
            "resume_skill": item.candidate_skill,
            "similarity": item.similarity,
        }
        for item in scored.semantic_matches
    ]


def _strengths(text: str, found: list[str]) -> list[str]:
    if not found:
        return ["No required skill was found in the resume text, so no strength is claimed."]
    projects = section_text(text, "projects")
    strengths = [f"The resume text includes {skill}." for skill in found]
    for skill in found:
        if projects and skill_in_text(skill, projects):
            strengths.append(f"The projects section includes {skill}.")
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        if not _QUANTIFIED.search(sentence):
            continue
        mentioned = next((skill for skill in found if skill_in_text(skill, sentence)), None)
        if mentioned:
            strengths.append(f"A measured result in the resume mentions {mentioned}.")
            break
    return strengths[:6]


def _gaps(missing: list[str], related: list[dict], keywords_missing: list[str]) -> list[str]:
    related_by = {item["required_skill"]: item for item in related}
    gaps = []
    for skill in missing:
        item = related_by.get(skill)
        if item:
            gaps.append(
                f"The resume uses {item['resume_skill']}, which is related to {skill}, "
                f"but {skill} itself was not found. Do not rename it unless that name is accurate."
            )
        else:
            gaps.append(f"{skill} was not found in the resume. Do not add it unless you have used it.")
    for word in keywords_missing[:4]:
        gaps.append(f'The job description uses "{word}", which was not found in the resume.')
    return gaps


def _suggestions(text: str, found: list[str], missing: list[str]) -> list[str]:
    items = []
    if section_text(text, "summary") == "" and "summary" not in text.casefold():
        items.append("Add a professional summary in your own words.")
    if section_text(text, "projects"):
        items.append("Make project descriptions more specific about what you built and which tools you used.")
    else:
        items.append("If you have projects, describe what you built. Do not invent a project.")
    items.append("Include measurable achievements only when they are true. Do not invent numbers.")
    if found:
        items.append(f"Keep {', '.join(found[:4])} visible where the resume already supports them.")
    if missing:
        items.append(f"Do not add {', '.join(missing[:4])} unless your own experience supports them.")
    items.append("Where the selected job description matches work you have done, use those words in the resume.")
    return items


def _keywords(description: str | None) -> list[str]:
    words = re.findall(r"[a-z][a-z0-9+]{3,}", _normalize(description or ""))
    chosen: list[str] = []
    for word in words:
        if word in _STOP_WORDS or word in chosen:
            continue
        chosen.append(word)
        if len(chosen) == 8:
            break
    return chosen


def _unique(values) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        if not isinstance(value, str):
            continue
        cleaned = " ".join(value.split())
        key = _normalize(cleaned)
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(cleaned)
    return unique


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())
