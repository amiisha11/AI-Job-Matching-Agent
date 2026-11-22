"""Checklist for extracted resume text.

The indicator is the share of checks that passed. It does not claim that a
resume will pass an applicant tracking system, and it does not call Gemini.
"""

import re

HEALTH_CHECK_COUNT = 8
HEALTH_FORMULA = (
    "Each of the 8 checks counts equally. The indicator is the percentage of checks that passed, "
    "rounded to the nearest whole number, with halves rounded up. "
    "Projects and quantified achievements are included so you can see them. "
    "A miss on those two is explained because they do not apply to every background. "
    "This is a checklist in this application. It is not a claim that the resume will pass every applicant tracking system."
)

SECTION_HEADINGS = (
    ("summary", ("professional summary", "career summary", "career objective", "summary", "objective", "profile", "about me")),
    ("skills", ("technical skills", "core competencies", "key skills", "competencies", "technologies", "skills")),
    ("experience", ("professional experience", "work experience", "employment history", "work history", "experience", "employment")),
    ("education", ("academic background", "qualifications", "education")),
    ("projects", ("personal projects", "academic projects", "projects", "portfolio")),
)
_EMAIL = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
_PHONE = re.compile(r"(?:\+?\d[\d\s().-]{8,16}\d)")
_YEAR_RUN = re.compile(r"(?:19|20)\d{2}(?:\s+(?:19|20)\d{2})+")
_DEGREE = re.compile(r"\b(bachelor|master|b\.?\s?tech|b\.?\s?sc|m\.?\s?sc|ph\.?\s?d|university|college|diploma)\b", re.IGNORECASE)
_QUANTIFIED = re.compile(
    r"(\d+(?:\.\d+)?\s*%|\$\s*\d|\b\d{1,3}(?:,\d{3})+\b|"
    r"\b(?:increased|reduced|improved|saved|grew|cut|decreased)\b[^\n]{0,40}\d|"
    r"\d[^\n]{0,24}\b(?:percent|users|customers|requests|revenue|hours)\b)",
    re.IGNORECASE,
)


def nearest_percent(part: int, whole: int) -> int | None:
    """Round part / whole to a percent. Halves round up. Zero whole has no percent."""
    if whole <= 0:
        return None
    return (100 * part + whole // 2) // whole


def assess_resume(text: str) -> dict:
    """Score the extracted text with eight visible checks."""
    source = text if isinstance(text, str) else ""
    sections = _sections(source)
    checks = [
        _contact_check(source),
        _headed_check(
            "summary",
            "Professional summary",
            sections.get("summary"),
            "Looked for a heading such as Summary, Profile, or Objective.",
            "Add a professional summary in your own words.",
            minimum_letters=40,
        ),
        _skills_check(sections.get("skills")),
        _headed_check(
            "experience",
            "Work experience",
            sections.get("experience"),
            "Looked for a heading such as Experience, Employment, or Work history.",
            "Add a work experience section that describes roles you have actually held.",
            minimum_letters=40,
        ),
        _education_check(source, sections.get("education")),
        _optional_check(
            "projects",
            "Projects",
            sections.get("projects"),
            "Looked for a Projects or Portfolio heading.",
            "A projects section is useful for students, career changes, and roles that ask for one. "
            "Leave it out only when work experience already shows the same evidence.",
        ),
        _quantified_check(source),
        _readable_check(source),
    ]
    passed = sum(1 for check in checks if check["passed"])
    suggestions = [check["suggestion"] for check in checks if check.get("suggestion")]
    return {
        "score": nearest_percent(passed, HEALTH_CHECK_COUNT),
        "passed": passed,
        "total": HEALTH_CHECK_COUNT,
        "formula": HEALTH_FORMULA,
        "checks": checks,
        "suggestions": suggestions,
    }


def section_text(text: str, kind: str) -> str:
    """Return the body under one heading, or an empty string."""
    return _sections(text).get(kind, "")


def _sections(text: str) -> dict[str, str]:
    lines = text.splitlines()
    found: dict[str, str] = {}
    for index, line in enumerate(lines):
        kind = _heading_kind(line)
        if kind is None or kind in found:
            continue
        body: list[str] = []
        for follow in lines[index + 1 : index + 13]:
            if _heading_kind(follow) is not None:
                break
            body.append(follow)
        found[kind] = "\n".join(body).strip()[:1500]
    return found


def _heading_kind(line: str) -> str | None:
    key = " ".join(line.casefold().replace(":", " ").replace("-", " ").split())
    if not key or len(key) > 40:
        return None
    for kind, names in SECTION_HEADINGS:
        for name in sorted(names, key=len, reverse=True):
            if key == name:
                return kind
    return None


def _letters(value: str) -> int:
    return sum(character.isalpha() for character in value)


def _check(key: str, label: str, status: str, detail: str, suggestion: str = "") -> dict:
    return {
        "key": key,
        "label": label,
        "status": status,
        "passed": status == "found",
        "detail": detail,
        "suggestion": suggestion,
    }


def _contact_check(text: str) -> dict:
    found = _EMAIL.search(text) is not None or _has_phone(text)
    if found:
        return _check(
            "contact",
            "Contact information",
            "found",
            "An email address or phone number was found. The address itself is not repeated here.",
        )
    return _check(
        "contact",
        "Contact information",
        "missing",
        "No email address or phone number was found.",
        "Add an email address or phone number you are willing to share with an employer.",
    )


def _has_phone(text: str) -> bool:
    for match in _PHONE.finditer(text):
        raw = match.group()
        if _YEAR_RUN.fullmatch(raw.strip()):
            continue
        digits = re.sub(r"\D", "", raw)
        if 10 <= len(digits) <= 15:
            return True
    return False


def _headed_check(key: str, label: str, body: str | None, looked_for: str, suggestion: str, minimum_letters: int) -> dict:
    if body is None:
        return _check(key, label, "missing", looked_for, suggestion)
    if _letters(body) < minimum_letters:
        return _check(
            key,
            label,
            "incomplete",
            f"A {label.lower()} heading was found, but the text under it is very short. {looked_for}",
            suggestion,
        )
    return _check(key, label, "found", f"A {label.lower()} heading was found with text under it. {looked_for}")


def _skills_check(body: str | None) -> dict:
    looked_for = "Looked for a heading such as Skills, Technical skills, or Competencies."
    if body is None:
        return _check(
            "skills",
            "Skills section",
            "missing",
            looked_for,
            "Add a skills section that lists tools and skills your experience supports.",
        )
    tokens = [part.strip() for part in re.split(r"[\n,;|/•·]+", body) if part.strip()]
    if not tokens:
        return _check(
            "skills",
            "Skills section",
            "incomplete",
            f"A skills heading was found, but no skill names were found under it. {looked_for}",
            "List the skills you can support from work, education, or projects.",
        )
    return _check("skills", "Skills section", "found", f"A skills heading was found. {looked_for}")


def _education_check(text: str, body: str | None) -> dict:
    looked_for = "Looked for an Education heading or a degree or school mention."
    if body is not None and _letters(body) >= 20:
        return _check("education", "Education", "found", f"An education heading was found with text under it. {looked_for}")
    if body is not None:
        return _check(
            "education",
            "Education",
            "incomplete",
            f"An education heading was found, but the text under it is very short. {looked_for}",
            "Name the school or qualification you completed. Leave out education only when it truly does not apply, and say so if a form asks.",
        )
    if _DEGREE.search(text):
        return _check("education", "Education", "found", looked_for)
    return _check(
        "education",
        "Education",
        "missing",
        looked_for,
        "Add education when you have a school or qualification to report. It may not apply to every background.",
    )


def _optional_check(key: str, label: str, body: str | None, looked_for: str, why: str) -> dict:
    if body is None:
        return _check(key, label, "missing", f"{looked_for} {why}", why)
    if _letters(body) < 40:
        return _check(
            key,
            label,
            "incomplete",
            f"A {label.lower()} heading was found, but the text under it is very short. {why}",
            "Make project descriptions more specific about what you built and which tools you used. Do not invent a project.",
        )
    return _check(key, label, "found", f"A {label.lower()} heading was found with text under it. {looked_for}")


def _quantified_check(text: str) -> dict:
    why = (
        "Quantified achievements are useful only when the numbers are true. "
        "A resume without figures is not automatically unsuitable."
    )
    if _QUANTIFIED.search(text):
        return _check("quantified", "Quantified achievements", "found", f"A number tied to a result was found. {why}")
    return _check("quantified", "Quantified achievements", "missing", why, "Include measurable achievements only when they are true. Do not invent numbers.")


def _readable_check(text: str) -> dict:
    letters = _letters(text)
    compact = len(re.sub(r"\s+", "", text))
    ratio = letters / compact if compact else 0
    if letters >= 200 and ratio >= 0.45:
        return _check(
            "readable",
            "Readable content",
            "found",
            "At least 200 letters were extracted, and most of the text is words rather than symbols.",
        )
    return _check(
        "readable",
        "Readable content",
        "missing",
        "Fewer than 200 letters were extracted, or the text is mostly symbols. The other checks may be incomplete.",
        "Export a text-based PDF if this file was a scan or the extraction looks incomplete.",
    )
