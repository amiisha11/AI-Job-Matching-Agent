"""Read public job listings from the Adzuna search API.

Credentials stay in the request and are never included in errors or logs.
This module does not write to the database.
"""

from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests

from settings import get_adzuna_app_id, get_adzuna_app_key

SEARCH_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
CATEGORIES_URL = "https://api.adzuna.com/v1/api/jobs/{country}/categories"
DEFAULT_TIMEOUT_SECONDS = 15


class AdzunaError(Exception):
    """A connection failure whose message contains no credentials."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class AdzunaCredentialsError(AdzunaError):
    """Raised before any request when an Adzuna setting is missing."""


class AdzunaAuthError(AdzunaError):
    """Raised when Adzuna rejects the application credentials."""


class AdzunaTimeoutError(AdzunaError):
    """Raised when Adzuna does not answer within the timeout."""


class AdzunaRateLimitError(AdzunaError):
    """Raised when Adzuna asks the client to slow down."""


@dataclass(frozen=True)
class AdzunaJob:
    """Fields that are safe to show from one Adzuna listing."""

    title: str
    company: str
    location: str
    created: str | None
    redirect_url: str | None
    external_id: str | None = None
    description: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    salary_is_predicted: bool | None = None
    contract_type: str | None = None
    contract_time: str | None = None
    workplace: str | None = None
    category_label: str | None = None
    category_tag: str | None = None


@dataclass(frozen=True)
class ProviderCategory:
    """One employment sector returned for one country. Tags are not shared by assumption."""

    country: str
    label: str
    tag: str


@dataclass(frozen=True)
class AdzunaSearch:
    """One completed search. `jobs` contains only the rows returned on this page."""

    status_code: int
    jobs: list[AdzunaJob]


def list_categories(
    *,
    country: str,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    session: requests.Session | None = None,
) -> list[ProviderCategory]:
    """Read the official category catalogue for one country. Nothing is stored."""
    app_id, app_key = _credentials()
    country_code = _country(country)
    url = CATEGORIES_URL.format(country=country_code)
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "content-type": "application/json",
    }
    response = _get(url, params, timeout, session)
    payload = _payload(response)
    rows = payload.get("results")
    if rows is None:
        rows = []
    if not isinstance(rows, list):
        raise AdzunaError("Adzuna response did not include a category list.")
    categories: list[ProviderCategory] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        label = _text(row.get("label"))
        tag = _text(row.get("tag"))
        if not label or not tag or tag in seen:
            continue
        seen.add(tag)
        categories.append(ProviderCategory(country_code, label, tag))
    return categories


def search_jobs(
    *,
    country: str = "gb",
    page: int = 1,
    what: str | None = None,
    results_per_page: int = 5,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    session: requests.Session | None = None,
    sort_by: str | None = None,
    sort_direction: str | None = None,
    max_days_old: int | None = None,
    category: str | None = None,
) -> AdzunaSearch:
    """Search one Adzuna country page. The caller chooses when this runs.

    A category tag comes from list_categories. It is sent as the documented
    `category` parameter. Keyword text stays optional when a tag is present.
    """
    app_id, app_key = _credentials()
    country_code = _country(country)
    page_number = _page(page)
    query = str(what or "").strip()
    category_tag = str(category or "").strip()
    if not query and not category_tag:
        raise AdzunaError("Adzuna search needs text or a category tag.")
    page_size = _page_size(results_per_page)
    url = SEARCH_URL.format(country=country_code, page=page_number)
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": page_size,
        "content-type": "application/json",
    }
    if query:
        params["what"] = query
    if category_tag:
        params["category"] = category_tag
    if sort_by:
        params["sort_by"] = _sort_by(sort_by)
    if sort_direction:
        params["sort_direction"] = _sort_direction(sort_direction)
    if max_days_old is not None:
        params["max_days_old"] = _max_days_old(max_days_old)
    response = _get(url, params, timeout, session)
    payload = _payload(response)
    jobs = _jobs(payload, page_size, (app_id, app_key))
    return AdzunaSearch(status_code=response.status_code, jobs=jobs)


def _credentials() -> tuple[str, str]:
    app_id = get_adzuna_app_id()
    app_key = get_adzuna_app_key()
    missing = [
        name
        for name, value in (("ADZUNA_APP_ID", app_id), ("ADZUNA_APP_KEY", app_key))
        if not value
    ]
    if missing:
        names = " and ".join(missing)
        verb = "is" if len(missing) == 1 else "are"
        raise AdzunaCredentialsError(f"{names} {verb} missing. Set it in the .env file.")
    return app_id, app_key


def _country(country: str) -> str:
    code = str(country or "").strip().lower()
    if len(code) != 2 or not code.isalpha():
        raise AdzunaError("Adzuna country must be a two-letter code.")
    return code


def _page(page: int) -> int:
    if isinstance(page, bool) or not isinstance(page, int) or page < 1:
        raise AdzunaError("Adzuna page must be 1 or greater.")
    return page


def _sort_by(value: str) -> str:
    allowed = {"date", "salary", "relevance"}
    choice = str(value or "").strip().lower()
    if choice not in allowed:
        raise AdzunaError("Adzuna sort_by must be date, salary, or relevance.")
    return choice


def _sort_direction(value: str) -> str:
    """Adzuna documents sort_direction as up or down. Down puts newer dates first."""
    choice = str(value or "").strip().lower()
    if choice not in {"up", "down"}:
        raise AdzunaError("Adzuna sort_direction must be up or down.")
    return choice


def _max_days_old(value: int) -> int:
    """Adzuna's max_days_old hides ads older than this many days. Callers opt in."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise AdzunaError("Adzuna max_days_old must be a whole number of days.")
    return value


def _page_size(results_per_page: int) -> int:
    if isinstance(results_per_page, bool) or not isinstance(results_per_page, int):
        raise AdzunaError("Adzuna results_per_page must be a whole number from 1 to 50.")
    if not 1 <= results_per_page <= 50:
        raise AdzunaError("Adzuna results_per_page must be a whole number from 1 to 50.")
    return results_per_page


def _get(url: str, params: dict, timeout: float, session: requests.Session | None):
    requester = session or requests
    try:
        response = requester.get(url, params=params, timeout=timeout)
    except requests.Timeout:
        raise AdzunaTimeoutError("The Adzuna request timed out.") from None
    except requests.RequestException:
        raise AdzunaError("The Adzuna request could not be completed.") from None
    if response.status_code == 429:
        raise AdzunaRateLimitError(
            "Adzuna rate limit reached with HTTP 429.",
            status_code=429,
        ) from None
    if response.status_code in (401, 403):
        raise AdzunaAuthError(
            f"Adzuna rejected the request with HTTP {response.status_code}.",
            status_code=response.status_code,
        ) from None
    if response.status_code >= 400:
        raise AdzunaError(
            f"Adzuna request failed with HTTP {response.status_code}.",
            status_code=response.status_code,
        ) from None
    return response


def _payload(response) -> dict:
    try:
        payload = response.json()
    except ValueError:
        raise AdzunaError("Adzuna returned a response that was not valid JSON.") from None
    if not isinstance(payload, dict):
        raise AdzunaError("Adzuna returned a response that was not valid JSON.")
    return payload


def _jobs(payload: dict, page_size: int, secrets: tuple[str, ...]) -> list[AdzunaJob]:
    rows = payload.get("results")
    if rows is None:
        rows = []
    if not isinstance(rows, list):
        raise AdzunaError("Adzuna response did not include a job list.")
    jobs: list[AdzunaJob] = []
    for row in rows[:page_size]:
        if not isinstance(row, dict):
            continue
        label, tag = _category(row)
        jobs.append(
            AdzunaJob(
                title=_text(row.get("title")),
                company=_label(row.get("company")),
                location=_label(row.get("location")),
                created=_optional_text(row.get("created")),
                redirect_url=_public_link(row.get("redirect_url"), secrets),
                external_id=_external_id(row.get("id")),
                description=_optional_text(row.get("description")),
                salary_min=_salary_bound(row, "salary_min"),
                salary_max=_salary_bound(row, "salary_max"),
                salary_currency=_optional_text(row.get("salary_currency") or row.get("currency")),
                salary_is_predicted=_predicted_salary(row.get("salary_is_predicted")),
                contract_type=_optional_text(row.get("contract_type")),
                contract_time=_optional_text(row.get("contract_time")),
                workplace=_workplace(row),
                category_label=label,
                category_tag=tag,
            )
        )
    return jobs


def _category(row: dict) -> tuple[str | None, str | None]:
    """Read the category object on a listing. A missing object stays empty."""
    value = row.get("category")
    if not isinstance(value, dict):
        return None, None
    return _optional_text(value.get("label")), _optional_text(value.get("tag"))


def _label(value) -> str:
    if isinstance(value, dict):
        return _text(value.get("display_name"))
    return _text(value)


def _text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _external_id(value) -> str | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return _optional_text(value)


def _predicted_salary(value) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    return str(value).strip() in {"1", "true", "True"}


def _salary_bound(row: dict, key: str) -> float | None:
    """Use a salary figure only when Adzuna did not mark it as predicted."""
    if _predicted_salary(row.get("salary_is_predicted")) is True:
        return None
    value = row.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _workplace(row: dict) -> str | None:
    """Read an explicit workplace field. Do not infer remote from the title."""
    for key in ("workplace", "work_type", "remote"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _optional_text(value) -> str | None:
    text = _text(value)
    return text or None


def _public_link(value, secrets: tuple[str, ...]) -> str | None:
    """Drop query values that repeat an Adzuna credential, including utm_source."""
    text = _optional_text(value)
    if text is None:
        return None
    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    hidden = {secret for secret in secrets if secret}
    query = [
        (key, item)
        for key, item in parse_qsl(parsed.query, keep_blank_values=True)
        if item not in hidden and key.lower() not in {"app_id", "app_key"}
    ]
    cleaned = urlunparse(parsed._replace(query=urlencode(query)))
    if any(secret and secret in cleaned for secret in hidden):
        cleaned = urlunparse(parsed._replace(query=""))
    return cleaned or None


class AdzunaSource:
    """One Adzuna search. Discovery uses this object so another provider can replace it."""

    name = "adzuna"

    def list_categories(self, *, country: str) -> list[ProviderCategory]:
        return list_categories(country=country)

    def search_listings(
        self,
        *,
        country: str,
        query: str,
        limit: int,
        sort_by: str | None = None,
        sort_direction: str | None = None,
        max_days_old: int | None = None,
        category: str | None = None,
        page: int = 1,
    ) -> AdzunaSearch:
        return search_jobs(
            country=country,
            page=page,
            what=query or None,
            results_per_page=limit,
            sort_by=sort_by,
            sort_direction=sort_direction,
            max_days_old=max_days_old,
            category=category,
        )
