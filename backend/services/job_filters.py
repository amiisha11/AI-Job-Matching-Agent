"""Filter stored jobs with the fields they actually have.

A missing category, workplace, salary, or employment type stays missing.
Titles are not used to guess an industry, a workplace, or an internship.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from services.search_catalog import COUNTRY_NAMES, DEFAULT_DISCOVERY_COUNTRIES


EXPERIENCE_OPTIONS = (
    {"value": "any", "label": "Any"},
    {"value": "entry", "label": "Internship / entry-level"},
    {"value": "0-2", "label": "0–2 years"},
    {"value": "3-5", "label": "3–5 years"},
    {"value": "5plus", "label": "5+ years"},
    {"value": "unspecified", "label": "Experience not specified"},
)
SORT_OPTIONS = (
    {"value": "newest", "label": "Newest first"},
    {"value": "match_score", "label": "Match score"},
)
WORKPLACE_LABELS = {
    "remote": "Remote",
    "hybrid": "Hybrid",
    "onsite": "Onsite",
}
EMPLOYMENT_LABELS = {
    "full_time": "Full-time",
    "part_time": "Part-time",
    "contract": "Contract",
    "temporary": "Temporary",
    "internship": "Internship",
    "permanent": "Permanent",
}
_EMPLOYMENT_TOKENS = {
    "full_time": "full_time",
    "part_time": "part_time",
    "contract": "contract",
    "temporary": "temporary",
    "temp": "temporary",
    "internship": "internship",
    "intern": "internship",
    "permanent": "permanent",
}


@dataclass(frozen=True)
class JobSearch:
    """One Discover query. Blank values mean the filter is not applied."""

    text: str = ""
    category: str = ""
    country: str = ""
    location: str = ""
    workplace: str = ""
    employment: str = ""
    experience: str = ""
    salary_currency: str = ""
    salary_min: float | None = None
    salary_max: float | None = None
    sort: str = ""


def search_from_params(params: dict) -> JobSearch:
    """Build a search from request values. Unknown sort names are ignored."""

    def clean(name: str) -> str:
        return " ".join(str(params.get(name) or "").split())

    category = clean("category")
    country = clean("country")
    workplace = clean("workplace")
    employment = clean("employment")
    experience = clean("experience")
    sort = clean("sort").casefold()
    return JobSearch(
        text=clean("q"),
        category="" if category.casefold() in {"", "all"} else category,
        country="" if country.casefold() in {"", "worldwide"} else country.casefold(),
        location=clean("location"),
        workplace="" if workplace.casefold() in {"", "any"} else workplace.casefold(),
        employment="" if employment.casefold() in {"", "any"} else employment.casefold(),
        experience="" if experience.casefold() in {"", "any"} else experience.casefold(),
        salary_currency=clean("salary_currency").upper(),
        salary_min=_optional_number(params.get("salary_min")),
        salary_max=_optional_number(params.get("salary_max")),
        sort="newest" if sort == "newest" else "",
    )


def salary_needs_currency(search: JobSearch) -> bool:
    """A number with no currency would mix or invent a currency."""
    return (search.salary_min is not None or search.salary_max is not None) and not search.salary_currency


def filter_jobs(jobs, search: JobSearch) -> list:
    """Return the listings that match. Newest ordering uses the posting date only."""
    matched = [job for job in jobs if job_matches(job, search)]
    if search.sort == "newest":
        return sorted(matched, key=_newest_key)
    return matched


def job_matches(job, search: JobSearch) -> bool:
    """True when every active filter agrees with the stored listing."""
    if search.country and _country(job) != search.country.casefold():
        return False
    if search.location and search.location.casefold() not in _text(_value(job, "location")).casefold():
        return False
    if not _category_matches(job, search.category):
        return False
    if search.workplace and _workplace(job) != search.workplace:
        return False
    if search.employment and search.employment not in _employment(job):
        return False
    if not _experience_matches(job, search.experience):
        return False
    if not _salary_matches(job, search):
        return False
    return _text_matches(job, search.text)


def build_filter_metadata(jobs, categories, category_error: str | None = None) -> dict:
    """Options the Discover page can show. Empty lists mean the stored rows do not have that fact."""
    industries = _industry_options(categories)
    if category_error and not industries:
        status = "unavailable"
    elif category_error:
        status = "partial"
    else:
        status = "ready"
    return {
        "categories": industries,
        "countries": _country_options(jobs),
        "workplaces": _option_list(_present_workplaces(jobs), WORKPLACE_LABELS),
        "employment_types": _option_list(_present_employment(jobs), EMPLOYMENT_LABELS),
        "experience": list(EXPERIENCE_OPTIONS),
        "salary_currencies": _currencies(jobs),
        "sorts": list(SORT_OPTIONS),
        "category_status": status,
        "category_error": category_error,
    }


def _industry_options(categories) -> list[dict]:
    grouped: dict[str, list[str]] = {}
    order: list[str] = []
    for item in categories or []:
        tag = _text(_value(item, "tag")).casefold()
        label = _text(_value(item, "label"))
        if not tag or not label:
            continue
        if tag not in grouped:
            grouped[tag] = []
            order.append(tag)
        if label not in grouped[tag]:
            grouped[tag].append(label)
    return [{"value": tag, "label": " / ".join(grouped[tag])} for tag in order]


def _country_options(jobs) -> list[dict]:
    codes = [code for code in DEFAULT_DISCOVERY_COUNTRIES]
    for job in jobs:
        code = _country(job)
        if code and code not in codes:
            codes.append(code)
    return [{"value": code, "label": COUNTRY_NAMES.get(code, code.upper())} for code in codes]


def _present_workplaces(jobs) -> list[str]:
    found = []
    for job in jobs:
        value = _workplace(job)
        if value and value not in found:
            found.append(value)
    return found


def _present_employment(jobs) -> list[str]:
    found = []
    for job in jobs:
        for value in _employment(job):
            if value not in found:
                found.append(value)
    return found


def _currencies(jobs) -> list[str]:
    found = []
    for job in jobs:
        currency = _text(_value(job, "salary_currency")).upper()
        if not currency or _amount(job) is None or currency in found:
            continue
        found.append(currency)
    return found


def _option_list(values, labels) -> list[dict]:
    return [{"value": value, "label": labels[value]} for value in values if value in labels]


def _category_matches(job, selected: str) -> bool:
    choice = selected.casefold()
    if choice in {"", "all"}:
        return True
    tag = _text(_value(job, "category_tag")).casefold()
    if choice in {"unspecified", "other"}:
        return not tag
    return tag == choice


def _experience_matches(job, selected: str) -> bool:
    choice = selected.casefold()
    if choice in {"", "any"}:
        return True
    known = _known_experience(job)
    if choice == "unspecified":
        return known is None
    if known is None:
        return False
    if choice == "entry":
        return known == 0
    if choice == "0-2":
        return 0 <= known <= 2
    if choice == "3-5":
        return 3 <= known <= 5
    if choice == "5plus":
        return known >= 5
    return False


def _known_experience(job) -> int | None:
    """Use a stored minimum only when the listing is matchable."""
    if _unmatchable(job):
        return None
    value = _value(job, "min_experience")
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _salary_matches(job, search: JobSearch) -> bool:
    if not search.salary_currency and search.salary_min is None and search.salary_max is None:
        return True
    currency = _text(_value(job, "salary_currency")).upper()
    amount = _amount(job)
    if not currency or amount is None:
        return False
    if search.salary_currency and currency != search.salary_currency.upper():
        return False
    if search.salary_min is not None and amount < search.salary_min:
        return False
    if search.salary_max is not None and amount > search.salary_max:
        return False
    return True


def _amount(job) -> float | None:
    for name in ("salary_min", "salary_max"):
        value = _value(job, name)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        return float(value)
    return None


def _text_matches(job, text: str) -> bool:
    needle = text.strip().casefold()
    if not needle:
        return True
    skills = _value(job, "required_skills") or []
    if not isinstance(skills, list):
        skills = []
    haystack = " ".join(
        [
            _text(_value(job, "title")),
            _text(_value(job, "company")),
            " ".join(_text(item) for item in skills),
        ]
    ).casefold()
    return needle in haystack


def _workplace(job) -> str:
    token = _token(_value(job, "workplace"))
    if token in {"on_site", "on-site"}:
        return "onsite"
    if token in WORKPLACE_LABELS:
        return token
    return ""


def _employment(job) -> set[str]:
    found = set()
    for name in ("contract_time", "contract_type"):
        token = _token(_value(job, name))
        mapped = _EMPLOYMENT_TOKENS.get(token)
        if mapped:
            found.add(mapped)
    return found


def _unmatchable(job) -> bool:
    if _value(job, "is_matchable") is False or _value(job, "requirements_available") is False:
        return True
    return str(_value(job, "matchability_status") or "").casefold() == "unmatchable"


def _country(job) -> str:
    return _text(_value(job, "source_country")).casefold()


def _newest_key(job):
    posted = _posted(job)
    identifier = _value(job, "id")
    number = identifier if isinstance(identifier, int) and not isinstance(identifier, bool) else 0
    if posted is None:
        return (1, 0, -number)
    return (0, -posted.timestamp(), -number)


def _posted(job) -> datetime | None:
    value = _value(job, "posted_at")
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _optional_number(value) -> float | None:
    if value is None or isinstance(value, bool) or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except ValueError:
        return None


def _token(value) -> str:
    return _text(value).casefold().replace("-", "_").replace(" ", "_")


def _text(value) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def _value(item, name: str):
    if isinstance(item, dict):
        return item.get(name)
    return getattr(item, name, None)
