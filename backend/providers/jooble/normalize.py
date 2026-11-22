"""Turn one Jooble row into the fields Discover already understands.

Missing company, location, salary, and category stay missing. A snippet is not
turned into verified skills.
"""

import re
from dataclasses import dataclass
from hashlib import sha256
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

_TAG = re.compile(r"<[^>]+>")
_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
_RUPEE = re.compile(r"\brs\.?\b", re.IGNORECASE)
_EMPLOYMENT = {
    "full-time": "full_time",
    "full time": "full_time",
    "fulltime": "full_time",
    "part-time": "part_time",
    "part time": "part_time",
    "parttime": "part_time",
    "contract": "contract",
    "temporary": "temporary",
    "temp": "temporary",
    "internship": "internship",
    "intern": "internship",
    "permanent": "permanent",
}
_TRACKING = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"}


@dataclass(frozen=True)
class JoobleJob:
    """One live listing. It is not a database row."""

    id: str
    title: str
    company: str
    location: str
    description: str | None
    source_url: str | None
    external_job_id: str | None
    source_country: str
    posted_at: str | None
    publisher: str | None
    salary_min: float | None
    salary_max: float | None
    salary_currency: str | None
    contract_time: str | None

    def as_dict(self) -> dict:
        """The public job shape, with match scoring left unavailable."""
        return {
            "id": self.id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "description": self.description,
            "required_skills": [],
            "min_experience": 0,
            "source": "jooble",
            "external_job_id": self.external_job_id,
            "source_country": self.source_country,
            "source_url": self.source_url,
            "posted_at": self.posted_at,
            "publisher": self.publisher,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "salary_currency": self.salary_currency,
            "contract_time": self.contract_time,
            "category_label": None,
            "category_tag": None,
            "is_matchable": False,
            "matchability_status": "unmatchable",
            "matchability_reason": "Jooble supplied a description snippet without verified skill requirements.",
            "description_is_snippet": True,
            "requirements_available": False,
        }


def normalize_jobs(rows, country: str) -> list[JoobleJob]:
    """Keep rows that have a title. Duplicate rows in one response are removed."""
    jobs = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        job = _one(row, country)
        if job is not None:
            jobs.append(job)
    return dedupe_jobs(jobs)


def dedupe_jobs(jobs, existing=None) -> list:
    """Drop a repeated URL, external id, or full title-company-location triple.

    The same title alone is not enough. Existing catalogue rows are left in place.
    """
    seen_urls = set()
    seen_ids = set()
    seen_triples = set()
    for job in existing or []:
        _remember(job, seen_urls, seen_ids, seen_triples)
    kept = []
    for job in jobs:
        url, external, triple = _keys(job)
        if url and url in seen_urls:
            continue
        if external and external in seen_ids:
            continue
        if triple and triple in seen_triples:
            continue
        _remember(job, seen_urls, seen_ids, seen_triples)
        kept.append(job)
    return kept


def normalize_url(value) -> str:
    """Compare links without tracking parameters or a trailing slash."""
    raw = str(value or "").strip()
    if not raw.lower().startswith(("http://", "https://")):
        return ""
    parsed = urlparse(raw)
    if not parsed.netloc:
        return ""
    query = [
        (key, item)
        for key, item in parse_qsl(parsed.query, keep_blank_values=True)
        if key.casefold() not in _TRACKING
    ]
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", urlencode(query), ""))


def _one(row: dict, country: str) -> JoobleJob | None:
    title = _plain(row.get("title"))
    if not title:
        return None
    company = _plain(row.get("company"))
    location = _plain(row.get("location"))
    link = _link(row.get("link"))
    external = _plain(row.get("id"))
    identity = external or normalize_url(link) or "|".join((title.casefold(), company.casefold(), location.casefold()))
    digest = sha256(f"{country}:{identity}".encode()).hexdigest()[:16]
    low, high, currency = _salary(row.get("salary"))
    return JoobleJob(
        id=f"jooble-{country}-{digest}",
        title=title,
        company=company,
        location=location,
        description=_plain(row.get("snippet")) or None,
        source_url=link,
        external_job_id=external or None,
        source_country=country,
        posted_at=_plain(row.get("updated")) or None,
        publisher=_plain(row.get("source")) or None,
        salary_min=low,
        salary_max=high,
        salary_currency=currency,
        contract_time=_employment(row.get("type")),
    )


def _salary(value) -> tuple[float | None, float | None, str | None]:
    text = _plain(value)
    if not text:
        return None, None, None
    lowered = text.casefold()
    found = set()
    if "£" in text or "gbp" in lowered:
        found.add("GBP")
    if "₹" in text or "inr" in lowered or _RUPEE.search(lowered):
        found.add("INR")
    if "€" in text or "eur" in lowered:
        found.add("EUR")
    if "usd" in lowered:
        found.add("USD")
    if len(found) != 1:
        return None, None, None
    numbers = []
    for token in _NUMBER.findall(text):
        try:
            numbers.append(float(token.replace(",", "")))
        except ValueError:
            continue
    if not numbers:
        return None, None, None
    currency = found.pop()
    if len(numbers) == 1:
        return numbers[0], None, currency
    return min(numbers[0], numbers[1]), max(numbers[0], numbers[1]), currency


def _employment(value) -> str | None:
    token = _plain(value).casefold()
    return _EMPLOYMENT.get(token)


def _link(value) -> str | None:
    text = str(value or "").strip()
    if text.lower().startswith(("http://", "https://")):
        return text
    return None


def _plain(value) -> str:
    return " ".join(_TAG.sub(" ", str(value or "")).split())


def _keys(job):
    data = job.as_dict() if isinstance(job, JoobleJob) else job
    if not isinstance(data, dict):
        return "", None, None
    url = normalize_url(data.get("source_url"))
    external = _plain(data.get("external_job_id"))
    source = _plain(data.get("source")).casefold()
    country = _plain(data.get("source_country")).casefold()
    identity = (source, country, external) if external else None
    title = _plain(data.get("title")).casefold()
    company = _plain(data.get("company")).casefold()
    location = _plain(data.get("location")).casefold()
    triple = (title, company, location) if title and company and location else None
    return url, identity, triple


def _remember(job, urls, ids, triples) -> None:
    url, identity, triple = _keys(job)
    if url:
        urls.add(url)
    if identity:
        ids.add(identity)
    if triple:
        triples.add(triple)
