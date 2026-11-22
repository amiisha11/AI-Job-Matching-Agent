"""Completion figures for the signed-in profile.

Each figure is derived from fields the profile API already returns.
A missing value stays incomplete. Nothing here invents a skill or a score.
"""

COMPLETION_EXPLANATION = (
    "Six sections are counted: contact details, education and background, skills, "
    "career preferences, location preferences, and experience. A section is filled "
    "only when that part of the saved profile has a value. The percentage is the "
    "number of filled sections divided by six."
)

SECTION_SUGGESTIONS = {
    "Contact details": "Save your name and email.",
    "Education and background": "Add an education level, degree, or field of study.",
    "Skills": "Add at least one skill.",
    "Career preferences": "Add a preferred role or an industry from the provider catalogue.",
    "Location preferences": "Add a city, region, country, or remote preference.",
    "Experience": "Save your years of experience. Less than one year counts.",
}

SKILL_NOTE = (
    "Skills are shown as they were saved. Categories and proficiency levels are "
    "not stored, so they are not shown."
)


def _text(value) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())


def _saved_items(value) -> list[str]:
    if not isinstance(value, list):
        return []
    kept = []
    for item in value:
        cleaned = _text(item)
        if cleaned:
            kept.append(cleaned)
    return kept


def _saved_email(value) -> bool:
    email = value.strip().lower() if isinstance(value, str) else ""
    if not email or len(email) > 320 or "@" not in email:
        return False
    local, _, domain = email.partition("@")
    return bool(local) and "." in domain and " " not in email


def experience_text(years) -> str | None:
    """Label a stored year count. Zero is the saved answer for less than one year."""
    if isinstance(years, bool) or not isinstance(years, int) or years < 0:
        return None
    if years == 0:
        return "Less than 1 year"
    if years == 1:
        return "1 year"
    return f"{years} years"


def profile_sections(profile: dict) -> list[dict]:
    """Six completion checks. Each one is filled or not from the saved profile."""
    contact = bool(_text(profile.get("name"))) and _saved_email(profile.get("email"))
    education = _text(profile.get("education"))
    education_filled = bool(education) and education.casefold() not in {"not specified", "other"}
    education_filled = education_filled or any(
        _text(profile.get(field)) for field in ("degree", "field_of_study", "institution")
    )
    skills = _saved_items(profile.get("skills"))
    roles = _saved_items(profile.get("preferred_roles"))
    industries = _saved_items(profile.get("preferred_industries"))
    locations = _saved_items(profile.get("preferred_locations"))
    countries = _saved_items(profile.get("preferred_countries"))
    remote = _text(profile.get("remote_preference")).casefold()
    experience = experience_text(profile.get("years_experience"))
    return [
        {"label": "Contact details", "complete": contact},
        {"label": "Education and background", "complete": education_filled},
        {"label": "Skills", "complete": bool(skills)},
        {"label": "Career preferences", "complete": bool(roles or industries)},
        {"label": "Location preferences", "complete": bool(locations or countries or remote in {"remote", "hybrid", "onsite"})},
        {"label": "Experience", "complete": experience is not None},
    ]


def section_suggestions(sections: list[dict]) -> list[str]:
    """One next step for each section that is still empty."""
    return [
        SECTION_SUGGESTIONS[section["label"]]
        for section in sections
        if not section["complete"] and section["label"] in SECTION_SUGGESTIONS
    ]


def completion_percent(sections: list[dict]) -> int:
    """Share of filled sections, rounded to the nearest whole number."""
    if not sections:
        return 0
    filled = sum(1 for section in sections if section["complete"])
    return round(100 * filled / len(sections))


def filled_section_count(sections: list[dict]) -> int:
    return sum(1 for section in sections if section["complete"])
