"""Small display helpers shared by the five app pages.

Scores shown here are copied from API payloads. This module does not score jobs.
"""

import html
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

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


def jooble_attribution(job) -> str:
    """Credit Jooble on a live result and link to the regional site."""
    if not isinstance(job, dict) or str(job.get("source") or "").casefold() != "jooble":
        return ""
    country = str(job.get("source_country") or "").strip().casefold()
    href = "https://in.jooble.org/" if country == "in" else "https://uk.jooble.org/"
    safe_href = html.escape(href, quote=True)
    return (
        f"<a class='adzuna-credit' href='{safe_href}' target='_blank' rel='noopener noreferrer'>Jooble</a>"
    )


def observed_filter_options(jobs) -> dict:
    """Workplace, employment, and experience values actually present on these listings."""
    workplaces = []
    employment = []
    bands = []
    for job in jobs or []:
        if not isinstance(job, dict):
            continue
        workplace = _known_workplace(job)
        if workplace and workplace not in workplaces:
            workplaces.append(workplace)
        for kind in _known_employment(job):
            if kind not in employment:
                employment.append(kind)
        for band in _experience_bands(job):
            if band not in bands:
                bands.append(band)
    experience = []
    if bands:
        experience.append({"value": "any", "label": "Any"})
        labels = {
            "entry": "Internship / entry-level",
            "0-2": "0–2 years",
            "3-5": "3–5 years",
            "5plus": "5+ years",
        }
        experience.extend({"value": band, "label": labels[band]} for band in ("entry", "0-2", "3-5", "5plus") if band in bands)
    return {
        "workplaces": [{"value": value, "label": WORKPLACE_LABELS[value]} for value in workplaces],
        "employment_types": [{"value": value, "label": EMPLOYMENT_LABELS[value]} for value in employment],
        "experience": experience,
    }


def keep_jobs_for_filters(jobs, workplace: str, employment: str, experience: str) -> list:
    """Apply a selected detail filter. A missing field does not count as a match."""
    kept = []
    for job in jobs or []:
        if not isinstance(job, dict):
            continue
        if workplace not in {"", "any"} and _known_workplace(job) != workplace:
            continue
        if employment not in {"", "any"} and employment not in _known_employment(job):
            continue
        if experience not in {"", "any"} and not _experience_selected(job, experience):
            continue
        kept.append(job)
    return kept


def _known_workplace(job: dict) -> str:
    token = " ".join(str(job.get("workplace") or "").split()).casefold().replace("-", "_").replace(" ", "_")
    if token in {"on_site"}:
        token = "onsite"
    return token if token in WORKPLACE_LABELS else ""


def _known_employment(job: dict) -> set[str]:
    found = set()
    aliases = {"temp": "temporary", "intern": "internship"}
    for name in ("contract_time", "contract_type"):
        token = " ".join(str(job.get(name) or "").split()).casefold().replace("-", "_").replace(" ", "_")
        token = aliases.get(token, token)
        if token in EMPLOYMENT_LABELS:
            found.add(token)
    return found


def _experience_bands(job: dict) -> set[str]:
    """Bands for a stored minimum. A snippet or an unmatchable listing has none."""
    if job_is_unmatchable(job):
        return set()
    value = job.get("min_experience")
    if isinstance(value, bool) or not isinstance(value, int):
        return set()
    found = set()
    if value == 0:
        found.add("entry")
    if 0 <= value <= 2:
        found.add("0-2")
    if 3 <= value <= 5:
        found.add("3-5")
    if value >= 5:
        found.add("5plus")
    return found


def _experience_selected(job: dict, selected: str) -> bool:
    if selected == "unspecified":
        return not _experience_bands(job)
    return selected in _experience_bands(job)


def omit_repeated_jobs(existing, incoming) -> list:
    """Keep a live row only when it is not the same listing already on screen."""
    urls, ids, triples = set(), set(), set()
    for job in existing or []:
        _remember_job(job, urls, ids, triples)
    kept = []
    for job in incoming or []:
        if not isinstance(job, dict):
            continue
        url, identity, triple = _job_keys(job)
        if (url and url in urls) or (identity and identity in ids) or (triple and triple in triples):
            continue
        _remember_job(job, urls, ids, triples)
        kept.append(job)
    return kept


def _remember_job(job, urls, ids, triples) -> None:
    if not isinstance(job, dict):
        return
    url, identity, triple = _job_keys(job)
    if url:
        urls.add(url)
    if identity:
        ids.add(identity)
    if triple:
        triples.add(triple)


def _job_keys(job: dict):
    url = _compare_url(job.get("source_url"))
    external = " ".join(str(job.get("external_job_id") or "").split())
    source = str(job.get("source") or "").strip().casefold()
    country = str(job.get("source_country") or "").strip().casefold()
    identity = (source, country, external.casefold()) if external else None
    title = " ".join(str(job.get("title") or "").split()).casefold()
    company = " ".join(str(job.get("company") or "").split()).casefold()
    location = " ".join(str(job.get("location") or "").split()).casefold()
    triple = (title, company, location) if title and company and location else None
    return url, identity, triple


def _compare_url(value) -> str:
    raw = str(value or "").strip()
    if not raw.lower().startswith(("http://", "https://")):
        return ""
    parsed = urlparse(raw)
    if not parsed.netloc:
        return ""
    query = urlencode(
        [
            (key, item)
            for key, item in parse_qsl(parsed.query, keep_blank_values=True)
            if key.casefold() not in {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"}
        ]
    )
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", query, ""))


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


def _is_jooble(job) -> bool:
    return isinstance(job, dict) and str(job.get("source") or "").casefold() == "jooble"


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
    elif _is_adzuna(job) or _is_jooble(job):
        lines.append(EMPLOYMENT_NOT_SPECIFIED)
    if not real_skills(job) and (job_is_unmatchable(job) or _is_adzuna(job) or _is_jooble(job)):
        lines.append(SKILLS_NOT_PROVIDED)
    if _is_jooble(job):
        country_code = str(job.get("source_country") or "").strip().casefold()
        country = COUNTRY_NAMES.get(country_code, country_code.upper() or "Not provided")
        publisher = " ".join(str(job.get("publisher") or "").split())
        lines.extend(["Source: Jooble", f"Country: {country}", f"Updated: {_posted_label(job.get('posted_at'))}"])
        if publisher:
            lines.append(f"Publisher: {publisher}")
        if salary_label(job) != SALARY_NOT_PROVIDED:
            lines.append(salary_label(job))
        lines.append(workplace_label(job))
    elif _is_adzuna(job):
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
