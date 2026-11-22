"""Search several roles and countries without writing to the database.

One failed country or query does not cancel the others. Listings are
deduplicated by provider, country, and external id, and only when the
location and application URL also match.
"""

import time
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, urlunparse

from services.adzuna import AdzunaError, AdzunaJob, AdzunaRateLimitError, AdzunaSource, ProviderCategory
from services.search_catalog import OLD_LISTING_DAYS, RoleSearch
from settings import get_adzuna_app_id, get_adzuna_app_key

PROVIDER = "adzuna"
DATE_SORT = "date"
NEWEST_FIRST = "down"
RATE_LIMIT_RETRIES = 2
QUOTA_STOP_AFTER = 3
_SAFE_FAILURE = "The Adzuna request could not be completed."
_QUOTA_STOP = "Stopped after repeated Adzuna rate limits."


@dataclass(frozen=True)
class SearchAttempt:
    """The outcome of one country and one search phrase."""

    country: str
    query: str
    category: str
    status: str
    status_code: int | None
    fetched: int
    error_message: str | None


@dataclass(frozen=True)
class DiscoveredJob:
    """A provider listing kept for review. Required skills are not invented."""

    source: str
    external_job_id: str
    country: str
    title: str
    company: str
    location: str
    description: str | None
    description_status: str
    source_url: str | None
    posted_at: datetime | None
    posting_status: str
    salary_min: float | None
    salary_max: float | None
    salary_currency: str | None
    salary_status: str
    contract_type: str | None
    contract_time: str | None
    workplace: str | None
    queries: tuple[str, ...]
    categories: tuple[str, ...]
    category_label: str | None = None
    category_tag: str | None = None


@dataclass(frozen=True)
class DiscoverySummary:
    """Counts for one dry-run. This object is not stored."""

    attempts: tuple[SearchAttempt, ...]
    jobs: tuple[DiscoveredJob, ...]
    requests_attempted: int
    requests_succeeded: int
    requests_failed: int
    countries_succeeded: tuple[str, ...]
    countries_failed: tuple[str, ...]
    fetched: int
    unique: int
    cross_query_duplicates: int
    kept_separate: int
    by_country: dict[str, int]
    by_category: dict[str, int]
    missing_required_skills: int
    incomplete_descriptions: int
    missing_descriptions: int
    old_listings: int
    undated_listings: int
    wrote: bool = False
    http_requests: int = 0


def discover_jobs(
    *,
    countries: list[str],
    searches: list[RoleSearch],
    limit: int,
    sort_by: str | None = DATE_SORT,
    source: AdzunaSource | None = None,
    pause_seconds: float = 1.0,
    sleep=time.sleep,
    now=None,
    max_days_old: int | None = None,
) -> DiscoverySummary:
    """Call the provider once per country and role. Nothing is saved."""
    if not countries:
        raise RuntimeError("Choose at least one country.")
    if not searches:
        raise RuntimeError("Choose at least one search.")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 50:
        raise RuntimeError("The limit per query must be a whole number from 1 to 50.")
    provider = source or AdzunaSource()
    sort_direction = NEWEST_FIRST if sort_by == DATE_SORT else None
    clock = _now(now)
    attempts: list[SearchAttempt] = []
    jobs: list[DiscoveredJob] = []
    seen: dict[tuple, DiscoveredJob] = {}
    order: list[tuple] = []
    cross_query = 0
    kept_separate = 0
    first = True

    for country in countries:
        code = str(country or "").strip().lower()
        for search in searches:
            if not first and pause_seconds > 0:
                sleep(pause_seconds)
            first = False
            try:
                result = provider.search_listings(
                    country=code,
                    query=search.query,
                    limit=limit,
                    sort_by=sort_by,
                    sort_direction=sort_direction,
                    max_days_old=max_days_old,
                )
            except AdzunaRateLimitError as exc:
                attempts.append(_failed(code, search, exc))
                if pause_seconds > 0:
                    sleep(max(pause_seconds * 3, 3))
                continue
            except AdzunaError as exc:
                attempts.append(_failed(code, search, exc))
                continue
            except Exception:
                attempts.append(
                    SearchAttempt(code, search.query, search.category, "error", None, 0, _SAFE_FAILURE)
                )
                continue
            listings = list(result.jobs)
            attempts.append(
                SearchAttempt(code, search.query, search.category, "success", result.status_code, len(listings), None)
            )
            for listing in listings:
                job = _discovered(listing, code, search, clock)
                if job is None:
                    continue
                identity = (job.source, job.country, job.external_job_id)
                place = (job.location, _listing_path(job.source_url))
                previous = seen.get((*identity, *place))
                if previous is not None:
                    cross_query += 1
                    seen[(*identity, *place)] = _remember_query(previous, search)
                    continue
                if any(key[:3] == identity for key in seen):
                    kept_separate += 1
                seen[(*identity, *place)] = job
                order.append((*identity, *place))

    unique = [seen[key] for key in order]
    return _summary(attempts, unique, cross_query, kept_separate)


def collect_categories(
    countries: list[str],
    *,
    source: AdzunaSource | None = None,
    pause_seconds: float = 1.0,
    sleep=time.sleep,
) -> tuple[tuple[ProviderCategory, ...], tuple[SearchAttempt, ...]]:
    """Read each country's official category catalogue. One failure does not stop the rest."""
    if not countries:
        raise RuntimeError("Choose at least one country.")
    provider = source or AdzunaSource()
    found: list[ProviderCategory] = []
    attempts: list[SearchAttempt] = []
    first = True
    for country in countries:
        code = str(country or "").strip().lower()
        if not first and pause_seconds > 0:
            sleep(pause_seconds)
        first = False
        try:
            rows = list(provider.list_categories(country=code))
        except AdzunaRateLimitError as exc:
            attempts.append(SearchAttempt(code, "", "categories", "error", exc.status_code, 0, _safe_message(str(exc))))
            if pause_seconds > 0:
                sleep(max(pause_seconds * 3, 3))
            continue
        except AdzunaError as exc:
            attempts.append(SearchAttempt(code, "", "categories", "error", exc.status_code, 0, _safe_message(str(exc))))
            continue
        except Exception:
            attempts.append(SearchAttempt(code, "", "categories", "error", None, 0, _SAFE_FAILURE))
            continue
        found.extend(rows)
        attempts.append(SearchAttempt(code, "", "categories", "success", 200, len(rows), None))
    return tuple(found), tuple(attempts)


def sample_categories(categories, count: int) -> list[ProviderCategory]:
    """Spread a small check across the catalogue that was actually returned."""
    rows = [item for item in categories if item.tag and item.label]
    if count < 1 or not rows:
        return []
    if len(rows) <= count:
        return rows
    if count == 1:
        return [rows[0]]
    step = (len(rows) - 1) / (count - 1)
    chosen: list[ProviderCategory] = []
    seen: set[tuple[str, str]] = set()
    for index in range(count):
        item = rows[round(index * step)]
        key = (item.country, item.tag)
        if key in seen:
            continue
        seen.add(key)
        chosen.append(item)
    return chosen


def discover_categories(
    *,
    countries: list[str],
    categories: list[ProviderCategory],
    limit: int,
    pages: int = 1,
    source: AdzunaSource | None = None,
    pause_seconds: float = 1.0,
    sleep=time.sleep,
    now=None,
    sort_by: str | None = DATE_SORT,
    max_days_old: int | None = None,
) -> DiscoverySummary:
    """Search by official category tags. Titles are not invented and nothing is saved."""
    if not countries:
        raise RuntimeError("Choose at least one country.")
    if isinstance(pages, bool) or not isinstance(pages, int) or not 1 <= pages <= 10:
        raise RuntimeError("The page count must be a whole number from 1 to 10.")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 50:
        raise RuntimeError("The limit per query must be a whole number from 1 to 50.")
    codes = {str(country).strip().lower() for country in countries}
    selected = [
        item
        for item in categories
        if item.country.strip().lower() in codes and item.tag and item.label
    ]
    if not selected:
        raise RuntimeError("Choose at least one category returned by the provider.")
    provider = source or AdzunaSource()
    sort_direction = NEWEST_FIRST if sort_by == DATE_SORT else None
    clock = _now(now)
    attempts: list[SearchAttempt] = []
    seen: dict[tuple, DiscoveredJob] = {}
    order: list[tuple] = []
    cross_query = 0
    kept_separate = 0
    http_requests = 0
    first = True
    consecutive_limits = 0
    stopped = False
    for item in selected:
        if stopped:
            attempts.append(SearchAttempt(item.country, item.tag, item.label, "stopped", 429, 0, _QUOTA_STOP))
            continue
        search = RoleSearch(item.label, item.tag)
        for page in range(1, pages + 1):
            if not first and pause_seconds > 0:
                sleep(pause_seconds)
            first = False
            result, failure, calls = _category_page(
                provider,
                item,
                search,
                limit=limit,
                page=page,
                sort_by=sort_by,
                sort_direction=sort_direction,
                max_days_old=max_days_old,
                pause_seconds=pause_seconds,
                sleep=sleep,
            )
            http_requests += calls
            if failure is not None:
                attempts.append(failure)
                if failure.status_code == 429:
                    consecutive_limits += 1
                    stopped = consecutive_limits >= QUOTA_STOP_AFTER
                else:
                    consecutive_limits = 0
                break
            consecutive_limits = 0
            listings = list(result.jobs)
            attempts.append(
                SearchAttempt(item.country, item.tag, item.label, "success", result.status_code, len(listings), None)
            )
            for listing in listings:
                if not listing.category_label or not listing.category_tag:
                    listing = replace(
                        listing,
                        category_label=listing.category_label or item.label,
                        category_tag=listing.category_tag or item.tag,
                    )
                job = _discovered(listing, item.country, search, clock)
                if job is None:
                    continue
                identity = (job.source, job.country, job.external_job_id)
                place = (job.location, _listing_path(job.source_url))
                previous = seen.get((*identity, *place))
                if previous is not None:
                    cross_query += 1
                    seen[(*identity, *place)] = _remember_query(previous, search)
                    continue
                if any(key[:3] == identity for key in seen):
                    kept_separate += 1
                seen[(*identity, *place)] = job
                order.append((*identity, *place))
    return _summary(
        attempts,
        [seen[key] for key in order],
        cross_query,
        kept_separate,
        http_requests=http_requests,
    )


def _category_page(provider, item, search, *, limit, page, sort_by, sort_direction, max_days_old, pause_seconds, sleep):
    """Search one category page. A rate limit is retried with exponential waits."""
    calls = 0
    for retry in range(RATE_LIMIT_RETRIES + 1):
        calls += 1
        try:
            result = provider.search_listings(
                country=item.country,
                query="",
                limit=limit,
                sort_by=sort_by,
                sort_direction=sort_direction,
                max_days_old=max_days_old,
                category=item.tag,
                page=page,
            )
        except AdzunaRateLimitError as exc:
            if retry >= RATE_LIMIT_RETRIES:
                return None, _failed(item.country, search, exc), calls
            if pause_seconds > 0:
                sleep(pause_seconds * (2 ** retry))
            continue
        except AdzunaError as exc:
            return None, _failed(item.country, search, exc), calls
        except Exception:
            return None, SearchAttempt(item.country, item.tag, item.label, "error", None, 0, _SAFE_FAILURE), calls
        return result, None, calls
    return None, SearchAttempt(item.country, item.tag, item.label, "error", 429, 0, _QUOTA_STOP), calls


def _failed(country: str, search: RoleSearch, exc: AdzunaError) -> SearchAttempt:
    return SearchAttempt(
        country,
        search.query,
        search.category,
        "error",
        exc.status_code,
        0,
        _safe_message(str(exc)),
    )


def _discovered(listing: AdzunaJob, country: str, search: RoleSearch, clock: datetime) -> DiscoveredJob | None:
    external_id = " ".join(str(listing.external_id or "").split())
    title = " ".join(str(listing.title or "").split())
    company = " ".join(str(listing.company or "").split())
    location = " ".join(str(listing.location or "").split())
    if not external_id or not title or not company or not location:
        return None
    description = listing.description.strip() if isinstance(listing.description, str) else None
    description = description or None
    posted_at = _posted_at(listing.created)
    salary_status = _salary_status(listing)
    return DiscoveredJob(
        source=PROVIDER,
        external_job_id=external_id[:80],
        country=country,
        title=title[:500],
        company=company[:500],
        location=location[:500],
        description=description,
        description_status="provider snippet" if description else "not supplied",
        source_url=listing.redirect_url,
        posted_at=posted_at,
        posting_status=_posting_status(posted_at, clock),
        salary_min=listing.salary_min,
        salary_max=listing.salary_max,
        salary_currency=listing.salary_currency,
        salary_status=salary_status,
        contract_type=listing.contract_type,
        contract_time=listing.contract_time,
        workplace=listing.workplace,
        queries=(search.query,),
        categories=(search.category,),
        category_label=getattr(listing, "category_label", None),
        category_tag=getattr(listing, "category_tag", None),
    )


def _remember_query(job: DiscoveredJob, search: RoleSearch) -> DiscoveredJob:
    queries = job.queries if search.query in job.queries else (*job.queries, search.query)
    categories = job.categories if search.category in job.categories else (*job.categories, search.category)
    return replace(job, queries=queries, categories=categories)


def _summary(attempts, jobs, cross_query: int, kept_separate: int, http_requests: int | None = None) -> DiscoverySummary:
    by_country: dict[str, int] = {}
    by_category: dict[str, int] = {}
    for job in jobs:
        by_country[job.country] = by_country.get(job.country, 0) + 1
        for category in job.categories:
            by_category[category] = by_category.get(category, 0) + 1
    provider_attempts = [item for item in attempts if item.status != "stopped"]
    succeeded = {item.country for item in attempts if item.status == "success"}
    failed = tuple(country for country in _country_order(attempts) if country not in succeeded)
    return DiscoverySummary(
        attempts=tuple(attempts),
        jobs=tuple(jobs),
        requests_attempted=len(provider_attempts),
        requests_succeeded=sum(item.status == "success" for item in provider_attempts),
        requests_failed=sum(item.status == "error" for item in provider_attempts),
        countries_succeeded=tuple(country for country in _country_order(attempts) if country in succeeded),
        countries_failed=failed,
        fetched=sum(item.fetched for item in attempts),
        unique=len(jobs),
        cross_query_duplicates=cross_query,
        kept_separate=kept_separate,
        by_country=by_country,
        by_category=by_category,
        missing_required_skills=len(jobs),
        incomplete_descriptions=sum(job.description_status != "full description" for job in jobs),
        missing_descriptions=sum(job.description_status == "not supplied" for job in jobs),
        old_listings=sum(job.posting_status == "older" for job in jobs),
        undated_listings=sum(job.posting_status == "not supplied" for job in jobs),
        http_requests=len(provider_attempts) if http_requests is None else http_requests,
    )


def _country_order(attempts) -> list[str]:
    ordered: list[str] = []
    for item in attempts:
        if item.country not in ordered:
            ordered.append(item.country)
    return ordered


def _listing_path(url: str | None) -> str:
    """Ignore tracking parameters. A different path is a different listing."""
    if not url:
        return ""
    parsed = urlparse(url)
    return urlunparse(parsed._replace(query="", fragment=""))


def _salary_status(listing: AdzunaJob) -> str:
    if listing.salary_is_predicted is True:
        return "predicted figure ignored"
    if listing.salary_min is None and listing.salary_max is None:
        return "not supplied"
    return "supplied"


def _posting_status(posted_at: datetime | None, clock: datetime) -> str:
    if posted_at is None:
        return "not supplied"
    if posted_at < clock - timedelta(days=OLD_LISTING_DAYS):
        return "older"
    return "recent"


def _posted_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _safe_message(message: str) -> str:
    text = message
    for secret in (get_adzuna_app_id(), get_adzuna_app_key()):
        if secret and secret in text:
            text = text.replace(secret, "[REDACTED]")
    return text or _SAFE_FAILURE


def _now(clock) -> datetime:
    if clock is None:
        return datetime.now(timezone.utc)
    if callable(clock):
        return clock()
    return clock
