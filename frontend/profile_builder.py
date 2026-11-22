"""Choices and checks for the My Profile form.

The lists below are suggestions. A custom entry is stored in the same text
fields the API already accepts.
"""

import re

EDUCATION_OPTIONS = [
    "Not specified",
    "B.Tech",
    "B.E.",
    "BCA",
    "MCA",
    "M.Tech",
    "B.Sc.",
    "M.Sc.",
    "Diploma",
    "Other",
]

SKILL_OPTIONS = [
    "Python",
    "Java",
    "JavaScript",
    "TypeScript",
    "SQL",
    "HTML",
    "CSS",
    "React",
    "Node.js",
    "FastAPI",
    "Django",
    "Flask",
    "Git",
    "Docker",
    "AWS",
    "Azure",
    "Linux",
    "C",
    "C++",
    "Machine Learning",
    "Data Analysis",
    "Excel",
    "Power BI",
    "Tableau",
    "Pandas",
    "PostgreSQL",
    "MongoDB",
    "REST APIs",
]

ROLE_OPTIONS = [
    "Software Engineer",
    "Frontend Engineer",
    "Backend Engineer",
    "Full Stack Developer",
    "Data Analyst",
    "Data Scientist",
    "Machine Learning Engineer",
    "Data Engineer",
    "DevOps Engineer",
    "QA Engineer",
    "Business Analyst",
    "Product Manager",
    "UI/UX Designer",
    "Android Developer",
    "iOS Developer",
]

LOCATION_OPTIONS = [
    "Remote",
    "Bengaluru",
    "Mumbai",
    "Delhi",
    "Hyderabad",
    "Pune",
    "Chennai",
    "Kolkata",
    "Noida",
    "Gurugram",
    "Ahmedabad",
    "Jaipur",
    "Chandigarh",
    "Kochi",
    "Indore",
]

DEGREE_OPTIONS = [
    "Not specified",
    "B.Tech",
    "B.E.",
    "BCA",
    "MCA",
    "M.Tech",
    "B.Sc.",
    "M.Sc.",
    "B.A.",
    "M.A.",
    "Diploma",
    "Other",
]

FIELD_OPTIONS = [
    "Not specified",
    "Computer Science",
    "Information Technology",
    "Mathematics",
    "Business",
    "Engineering",
    "Design",
    "Healthcare",
    "Law",
    "Education",
    "Science",
    "Other",
]

REMOTE_OPTIONS = ["Not specified", "Remote", "Hybrid", "Onsite"]
REMOTE_VALUES = {"remote": "remote", "hybrid": "hybrid", "onsite": "onsite"}

EXPERIENCE_YEARS = list(range(0, 31))
MAX_CUSTOM_LENGTH = 80
GRADUATION_MIN = 1950
GRADUATION_MAX = 2035
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def clean_text(value: str) -> str:
    """Collapse extra spaces and trim the ends."""
    return " ".join(str(value).split())


def include_custom(
    options: list[str],
    selected: list[str],
    raw: str,
    noun: str,
) -> tuple[list[str], list[str], str]:
    """Add a custom entry, or select the existing item when it is already listed."""
    cleaned = clean_text(raw)
    if not cleaned:
        return list(options), list(selected), f"Enter a {noun} to add."
    if len(cleaned) > MAX_CUSTOM_LENGTH:
        return list(options), list(selected), f"A {noun} must be {MAX_CUSTOM_LENGTH} characters or fewer."

    match = next((item for item in options if item.casefold() == cleaned.casefold()), None)
    chosen = match if match is not None else cleaned
    updated_options = list(options)
    if match is None:
        updated_options.append(chosen)
    updated_selected = list(selected)
    if all(item.casefold() != chosen.casefold() for item in updated_selected):
        updated_selected.append(chosen)
    return updated_options, updated_selected, ""


def dedupe_items(values: list[str]) -> list[str]:
    """Keep the first trimmed copy of each item, ignoring blank and repeated text."""
    return _clean_list(values)


def optional_choice(choice: str, custom: str, noun: str) -> tuple[str | None, str | None]:
    """Return a selected suggestion or a custom value. A blank optional field is skipped."""
    if not choice or choice == "Not specified":
        return None, None
    if choice == "Other":
        cleaned = clean_text(custom)
        if not cleaned:
            return None, None
        if len(cleaned) > MAX_CUSTOM_LENGTH:
            return None, f"{noun} must be {MAX_CUSTOM_LENGTH} characters or fewer."
        return cleaned, None
    cleaned = clean_text(choice)
    if len(cleaned) > MAX_CUSTOM_LENGTH:
        return None, f"{noun} must be {MAX_CUSTOM_LENGTH} characters or fewer."
    return cleaned, None


def optional_line(value: str, noun: str, limit: int = 120) -> tuple[str | None, str | None]:
    """Trim one optional text field. A blank value is left empty."""
    cleaned = clean_text(value or "")
    if not cleaned:
        return None, None
    if len(cleaned) > limit:
        return None, f"{noun} must be {limit} characters or fewer."
    return cleaned, None


def graduation_year_value(value) -> tuple[int | None, str | None]:
    """Accept a blank year or a four-digit year in the supported range."""
    if value is None:
        return None, None
    text = str(value).strip()
    if not text:
        return None, None
    if not text.isdigit():
        return None, "Graduation year must be a four-digit year, or left blank."
    year = int(text)
    if year < GRADUATION_MIN or year > GRADUATION_MAX:
        return None, f"Graduation year must be between {GRADUATION_MIN} and {GRADUATION_MAX}, or left blank."
    return year, None


def remote_value(choice: str) -> tuple[str | None, str | None]:
    """Store a remote preference without treating it as a city."""
    key = clean_text(choice or "").casefold()
    if not key or key == "not specified":
        return None, None
    if key not in REMOTE_VALUES:
        return None, "Choose Remote, Hybrid, Onsite, or leave the preference blank."
    return REMOTE_VALUES[key], None


def education_value(choice: str, custom: str) -> tuple[str | None, str | None]:
    """Return the education string for the API, or an error message."""
    if choice == "Not specified":
        return None, None
    if choice == "Other":
        cleaned = clean_text(custom)
        if not cleaned:
            return None, "Enter your education, or choose one from the list."
        if len(cleaned) > MAX_CUSTOM_LENGTH:
            return None, f"Education must be {MAX_CUSTOM_LENGTH} characters or fewer."
        return cleaned, None
    if choice not in EDUCATION_OPTIONS:
        return None, "Choose an education option."
    return choice, None


def profile_payload(
    name: str,
    email: str,
    education_choice: str,
    custom_education: str,
    skills: list[str],
    preferred_roles: list[str],
    preferred_locations: list[str],
    years_experience: int,
    *,
    degree_choice: str = "Not specified",
    custom_degree: str = "",
    field_choice: str = "Not specified",
    custom_field: str = "",
    specialization: str = "",
    institution: str = "",
    graduation_year: str = "",
    preferred_industries: list[str] | None = None,
    preferred_countries: list[str] | None = None,
    remote_choice: str = "Not specified",
) -> tuple[dict | None, str | None]:
    """Build the existing candidate create body, or return one validation message."""
    cleaned_name = clean_text(name)
    if not cleaned_name:
        return None, "Enter your name."
    if len(cleaned_name) > 200:
        return None, "Name must be 200 characters or fewer."

    cleaned_email = email.strip().lower()
    if not _EMAIL_PATTERN.fullmatch(cleaned_email):
        return None, "Enter an email address like name@example.com."
    if len(cleaned_email) > 320:
        return None, "Email must be 320 characters or fewer."

    education, education_error = education_value(education_choice, custom_education)
    if education_error:
        return None, education_error
    degree, degree_error = optional_choice(degree_choice, custom_degree, "Degree")
    if degree_error:
        return None, degree_error
    field_of_study, field_error = optional_choice(field_choice, custom_field, "Field of study")
    if field_error:
        return None, field_error
    specialization_text, specialization_error = optional_line(specialization, "Specialization")
    if specialization_error:
        return None, specialization_error
    institution_text, institution_error = optional_line(institution, "Institution")
    if institution_error:
        return None, institution_error
    graduation, graduation_error = graduation_year_value(graduation_year)
    if graduation_error:
        return None, graduation_error
    remote_preference, remote_error = remote_value(remote_choice)
    if remote_error:
        return None, remote_error
    if education is None and degree:
        education = degree

    try:
        years = int(years_experience)
    except (TypeError, ValueError):
        return None, "Choose a whole number of years."
    if years < 0:
        return None, "Years of experience cannot be negative."

    return {
        "name": cleaned_name,
        "email": cleaned_email,
        "education": education,
        "degree": degree,
        "field_of_study": field_of_study,
        "specialization": specialization_text,
        "institution": institution_text,
        "graduation_year": graduation,
        "skills": _clean_list(skills),
        "preferred_roles": _clean_list(preferred_roles),
        "preferred_industries": _clean_list(preferred_industries or []),
        "preferred_locations": _clean_list(preferred_locations),
        "preferred_countries": _clean_list(preferred_countries or []),
        "remote_preference": remote_preference,
        "years_experience": years,
    }, None


def _clean_list(values: list[str]) -> list[str]:
    """Keep the first trimmed copy of each item, ignoring blank and repeated text."""
    kept: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = clean_text(value)
        key = cleaned.casefold()
        if not cleaned or key in seen:
            continue
        seen.add(key)
        kept.append(cleaned)
    return kept
