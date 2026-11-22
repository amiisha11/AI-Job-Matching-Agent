"""Small display helpers shared by the five app pages.

Scores shown here are copied from API payloads. This module does not score jobs.
"""

import html

import streamlit as st

from auth_session import authed_request
from home_metrics import score_bucket


ADZUNA_SITES = {
    "gb": "https://www.adzuna.co.uk/",
    "uk": "https://www.adzuna.co.uk/",
    "in": "https://www.adzuna.in/",
    "us": "https://www.adzuna.com/",
    "au": "https://www.adzuna.com.au/",
    "ca": "https://www.adzuna.ca/",
    "de": "https://www.adzuna.de/",
    "fr": "https://www.adzuna.fr/",
    "nl": "https://www.adzuna.nl/",
    "br": "https://www.adzuna.com.br/",
    "za": "https://www.adzuna.co.za/",
}
SCORE_UNAVAILABLE = "Match score unavailable"
SCORE_UNAVAILABLE_REASON = (
    "This listing does not provide enough verified skill requirements for reliable matching."
)
SKILLS_NOT_PROVIDED = "Skills not provided by source"
EXPERIENCE_NOT_SPECIFIED = "Experience requirement not specified"
SALARY_NOT_PROVIDED = "Salary not provided"
WORKPLACE_NOT_SPECIFIED = "Work arrangement not specified"
EMPLOYMENT_NOT_SPECIFIED = "Employment type not specified"
INDUSTRY_NOT_SPECIFIED = "Other / Not specified"
EMPLOYMENT_LABELS = {
    "full_time": "Full-time",
    "part_time": "Part-time",
    "contract": "Contract",
    "temporary": "Temporary",
    "internship": "Internship",
    "permanent": "Permanent",
}
WORKPLACE_LABELS = {
    "remote": "Remote",
    "hybrid": "Hybrid",
    "onsite": "Onsite",
}
COUNTRY_NAMES = {
    "gb": "United Kingdom",
    "uk": "United Kingdom",
    "in": "India",
    "us": "United States",
    "au": "Australia",
    "ca": "Canada",
    "de": "Germany",
    "fr": "France",
    "nl": "Netherlands",
    "br": "Brazil",
    "za": "South Africa",
}


QUALITY_LABELS = {
    "81–100": "Strong match",
    "61–80": "Good match",
    "41–60": "Partial match",
    "21–40": "Limited match",
    "0–20": "Low match",
}


def initials(name: str) -> str:
    """Two letters from the candidate's saved name. A blank name has no initials."""
    parts = [part for part in str(name).split() if part]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0][:2].upper()
    return f"{parts[0][0]}{parts[-1][0]}".upper()


def job_is_unmatchable(job) -> bool:
    """True when the listing was stored without enough skill requirements to score."""
    if not isinstance(job, dict):
        return False
    if job.get("is_matchable") is False or job.get("requirements_available") is False:
        return True
    return str(job.get("matchability_status") or "").casefold() == "unmatchable"


def rankable_matches(matches) -> list:
    """Drop listings that must not appear as ranked scores."""
    if not isinstance(matches, list):
        return []
    return [
        match
        for match in matches
        if isinstance(match, dict) and not job_is_unmatchable(match.get("job") or {})
    ]


def unavailable_score_html(css_class: str = "discover-score") -> str:
    return (
        f"<p class='hero-lead {css_class}'>{SCORE_UNAVAILABLE}</p>"
        f"<p class='hero-lead'>{SCORE_UNAVAILABLE_REASON}</p>"
    )


def adzuna_attribution(job) -> str:
    """The Adzuna wordmark required on each displayed advert, linked to the local site."""
    if not isinstance(job, dict) or str(job.get("source") or "").casefold() != "adzuna":
        return ""
    country = str(job.get("source_country") or "gb").strip().casefold()
    href = ADZUNA_SITES.get(country, "https://www.adzuna.co.uk/")
    safe_href = html.escape(href, quote=True)
    return (
        f"<a class='adzuna-credit' href='{safe_href}' target='_blank' rel='noopener noreferrer'>Adzuna</a>"
    )


def original_listing_link(job) -> str:
    if not isinstance(job, dict):
        return ""
    url = str(job.get("source_url") or "").strip()
    if not url.lower().startswith(("http://", "https://")):
        return ""
    safe_url = html.escape(url, quote=True)
    return (
        f"<a class='adzuna-apply' href='{safe_url}' target='_blank' rel='noopener noreferrer'>"
        "View original listing</a>"
    )


def job_key(value):
    """Use one integer id for catalog rows and match rows."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return value


def real_skills(job) -> list[str]:
    if not isinstance(job, dict):
        return []
    return [
        skill.strip()
        for skill in job.get("required_skills") or []
        if isinstance(skill, str) and skill.strip() and skill.strip().casefold() != "none"
    ]


def experience_label(job) -> str:
    """Show a stored requirement. An unscored import does not turn 0 into a requirement."""
    if not isinstance(job, dict) or job_is_unmatchable(job):
        return EXPERIENCE_NOT_SPECIFIED
    value = job.get("min_experience")
    if value is None or str(value).strip().casefold() == "none":
        return EXPERIENCE_NOT_SPECIFIED
    return f"Minimum experience: {value} years"


def _is_adzuna(job) -> bool:
    return isinstance(job, dict) and str(job.get("source") or "").casefold() == "adzuna"


def _posted_label(value) -> str:
    text = str(value or "").strip()
    if not text or text.casefold() == "none":
        return "Posting date not provided"
    return text.replace("T", " ")[:16]


def industry_label(job) -> str:
    """Use a stored provider label or tag. A title is not an industry."""
    if not isinstance(job, dict):
        return INDUSTRY_NOT_SPECIFIED
    label = " ".join(str(job.get("category_label") or "").split())
    if label:
        return label
    tag = " ".join(str(job.get("category_tag") or "").split())
    if tag:
        return tag
    return INDUSTRY_NOT_SPECIFIED


def employment_label(job) -> str:
    """Show a stored contract value. Do not read the job title for this."""
    if not isinstance(job, dict):
        return ""
    found = []
    for name in ("contract_time", "contract_type"):
        token = " ".join(str(job.get(name) or "").split()).casefold().replace("-", "_").replace(" ", "_")
        label = EMPLOYMENT_LABELS.get(token)
        if label and label not in found:
            found.append(label)
    return ", ".join(found)


def salary_label(job) -> str:
    """Show a salary only when the listing includes both an amount and a currency."""
    if not isinstance(job, dict):
        return SALARY_NOT_PROVIDED
    currency = " ".join(str(job.get("salary_currency") or "").split())
    amounts = [job.get("salary_min"), job.get("salary_max")]
    numbers = [value for value in amounts if isinstance(value, (int, float)) and not isinstance(value, bool)]
    if not currency or not numbers:
        return SALARY_NOT_PROVIDED
    if len(numbers) == 2:
        return f"Salary: {_amount(numbers[0])}–{_amount(numbers[1])} {currency}"
    return f"Salary: {_amount(numbers[0])} {currency}"


def workplace_label(job) -> str:
    """Show Remote, Hybrid, or Onsite only when that word was stored."""
    if not isinstance(job, dict):
        return WORKPLACE_NOT_SPECIFIED
    token = " ".join(str(job.get("workplace") or "").split()).casefold().replace("-", "_").replace(" ", "_")
    if token in {"on_site"}:
        token = "onsite"
    label = WORKPLACE_LABELS.get(token)
    if not label:
        return WORKPLACE_NOT_SPECIFIED
    return f"Work arrangement: {label}"


def listing_notes_html(job) -> str:
    """Source facts and friendly text for fields the listing does not supply."""
    if not isinstance(job, dict):
        return ""
    lines = [f"Industry: {industry_label(job)}", experience_label(job)]
    employment = employment_label(job)
    if employment:
        lines.append(f"Employment type: {employment}")
    elif _is_adzuna(job):
        lines.append(EMPLOYMENT_NOT_SPECIFIED)
    if not real_skills(job) and (job_is_unmatchable(job) or _is_adzuna(job)):
        lines.append(SKILLS_NOT_PROVIDED)
    if _is_adzuna(job):
        country_code = str(job.get("source_country") or "").strip().casefold()
        country = COUNTRY_NAMES.get(country_code, country_code.upper() or "Not provided")
        lines.extend(
            [
                "Source: Adzuna",
                f"Country: {country}",
                f"Posted: {_posted_label(job.get('posted_at'))}",
                salary_label(job),
                workplace_label(job),
            ]
        )
    elif salary_label(job) != SALARY_NOT_PROVIDED:
        lines.append(salary_label(job))
    if not _is_adzuna(job) and workplace_label(job) != WORKPLACE_NOT_SPECIFIED:
        lines.append(workplace_label(job))
    return "".join(f"<p class='detail-line'>{html.escape(line)}</p>" for line in lines)


def _amount(value) -> str:
    number = float(value)
    if number.is_integer():
        return str(int(number))
    return str(number)


def match_quality(score: float) -> str:
    """Label a stored total score using the same ranges as the Home chart."""
    return QUALITY_LABELS[score_bucket(score)]


def matches_by_job(matches) -> dict[int, dict]:
    """Index ranked jobs by id. A missing ranking stays an empty index."""
    if not isinstance(matches, list):
        return {}
    indexed = {}
    for match in matches:
        job = match.get("job") if isinstance(match, dict) else None
        if isinstance(job, dict) and job.get("id") is not None:
            indexed[job_key(job["id"])] = match
    return indexed


def saved_job_ids(saved_jobs) -> set[int]:
    if not isinstance(saved_jobs, list):
        return set()
    found = set()
    for item in saved_jobs:
        job = item.get("job") if isinstance(item, dict) else None
        if isinstance(job, dict) and job.get("id") is not None:
            found.add(job_key(job["id"]))
    return found


def short_text(value, limit: int = 180) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def remember_saved(payload, job: dict) -> None:
    """Keep a confirmed save in the session list, or mark that list stale."""
    current = st.session_state.get("saved_jobs")
    if not isinstance(current, list) or not isinstance(payload, dict):
        st.session_state.saved_jobs = None
        return
    record = dict(payload)
    if not isinstance(record.get("job"), dict):
        record["job"] = job
    job_id = (record.get("job") or {}).get("id")
    kept = [item for item in current if (item.get("job") or {}).get("id") != job_id]
    st.session_state.saved_jobs = [record, *kept]


def save_job(job: dict) -> None:
    """Save one listing for the signed-in candidate. The button confirms only after the API does."""
    saved, save_error = authed_request(
        "POST",
        f"/jobs/{job['id']}/save",
        {"candidate_id": st.session_state.candidate_id},
    )
    if save_error:
        st.error(save_error)
        if "already saved" in save_error.casefold():
            st.session_state.saved_jobs = None
        return
    remember_saved(saved, job)
    st.success(f"Saved {job['title']}.")


def job_heading(job: dict, marker: str) -> str:
    title = html.escape(str(job.get("title") or ""))
    company = html.escape(str(job.get("company") or ""))
    location = html.escape(str(job.get("location") or ""))
    return (
        f"<h3 class='match-title {marker}'>{title}</h3>"
        f"<p class='match-company'>{company}</p>"
        f"<p class='match-location'>{location}</p>"
    )
