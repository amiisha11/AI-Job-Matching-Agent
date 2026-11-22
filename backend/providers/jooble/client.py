"""Call one Jooble regional endpoint. The API key stays in the URL and out of logs."""

import logging
from datetime import datetime, timezone

import requests

from providers.jooble.normalize import JoobleJob, normalize_jobs
from providers.jooble.quota import CACHE_SECONDS, cached, remember, reserve
from settings import get_jooble_api_key

LOGGER = logging.getLogger("jooble")
CONNECT_TIMEOUT_SECONDS = 5
READ_TIMEOUT_SECONDS = 15
PAGE_SIZE = "10"
REGIONS = {
    "in": ("https://in.jooble.org/api/{key}", "India"),
    "gb": ("https://uk.jooble.org/api/{key}", "United Kingdom"),
}


class JoobleError(Exception):
    """A search failure whose message contains no API key."""

    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message)
        self.status_code = status_code


def search_jobs(
    *,
    country: str,
    keywords: str,
    location: str | None = None,
    now: datetime | None = None,
    session: requests.Session | None = None,
    limit: int | None = None,
) -> list[JoobleJob]:
    """Search one country. India and the United Kingdom never share an endpoint or a key."""
    code = _country(country)
    query = " ".join(str(keywords or "").split())
    if not query:
        raise JoobleError("Enter a job title or keywords before searching Jooble.", 422)
    place = " ".join(str(location or "").split()) or REGIONS[code][1]
    moment = now or datetime.now(timezone.utc)
    cache_key = (code, query.casefold(), place.casefold())
    stored = cached(cache_key, moment)
    if stored is not None:
        return stored
    key = get_jooble_api_key(code)
    if not key:
        raise JoobleError("Jooble search is not configured for this country.")
    if not reserve(code, moment, limit if limit is not None else _default_limit()):
        raise JoobleError("The Jooble search limit for this country has been reached. Try again tomorrow.")
    url = REGIONS[code][0].format(key=key)
    payload = {
        "keywords": query,
        "location": place,
        "page": "1",
        "companysearch": False,
        "ResultOnPage": PAGE_SIZE,
    }
    try:
        response = _post(url, payload, session)
    except JoobleError:
        raise
    except requests.Timeout:
        LOGGER.warning("Jooble search failed: timeout country=%s", code)
        raise JoobleError("Jooble did not respond in time.") from None
    except requests.RequestException:
        LOGGER.warning("Jooble search failed: network country=%s", code)
        raise JoobleError("Jooble could not be reached.") from None
    jobs = _read(response, code, key)
    remember(cache_key, jobs, moment)
    return jobs


def _country(country: str) -> str:
    code = str(country or "").strip().casefold()
    if code == "uk":
        code = "gb"
    if code not in REGIONS:
        raise JoobleError("Jooble search is available for India and the United Kingdom.", 422)
    return code


def _post(url: str, payload: dict, session: requests.Session | None):
    client = session or requests
    return client.post(
        url,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=(CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS),
    )


def _read(response, country: str, key: str) -> list[JoobleJob]:
    status = response.status_code
    if status == 403:
        LOGGER.warning("Jooble search failed: unauthorized country=%s", country)
        raise JoobleError("Jooble rejected the API key for this country.")
    if status == 404:
        LOGGER.warning("Jooble search failed: endpoint country=%s", country)
        raise JoobleError("The Jooble endpoint for this country is unavailable.")
    if status == 429:
        LOGGER.warning("Jooble search failed: quota country=%s", country)
        raise JoobleError("Jooble has reached its request limit for this country. Try again tomorrow.")
    if status >= 400:
        LOGGER.warning("Jooble search failed: http country=%s", country)
        raise JoobleError("Jooble search is temporarily unavailable.")
    try:
        body = response.json()
    except ValueError:
        LOGGER.warning("Jooble search failed: invalid-json country=%s", country)
        raise JoobleError("Jooble returned a response that could not be read.") from None
    if not isinstance(body, dict) or not isinstance(body.get("jobs"), list):
        LOGGER.warning("Jooble search failed: invalid-json country=%s", country)
        raise JoobleError("Jooble returned a response that could not be read.")
    if key and key in str(body):
        LOGGER.warning("Jooble search failed: unexpected-body country=%s", country)
        raise JoobleError("Jooble returned a response that could not be read.")
    return normalize_jobs(body.get("jobs"), country)


def _default_limit() -> int:
    from providers.jooble.quota import DAILY_SAFETY_LIMIT

    return DAILY_SAFETY_LIMIT


# Re-export the cache window for tests that describe the quota behaviour.
__all__ = ["CACHE_SECONDS", "JoobleError", "search_jobs"]
