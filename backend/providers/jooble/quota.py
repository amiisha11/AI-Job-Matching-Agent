"""Count Jooble requests in memory. Listings are not stored."""

from datetime import date, datetime, timedelta, timezone

DAILY_SAFETY_LIMIT = 40
CACHE_SECONDS = 10 * 60
_COUNTS: dict[tuple[str, date], int] = {}
_CACHE: dict[tuple, tuple[datetime, list]] = {}


def reset() -> None:
    """Drop the in-memory counters. Tests use this between cases."""
    _COUNTS.clear()
    _CACHE.clear()


def cached(key: tuple, now: datetime):
    """Return a recent result for the same search, if one is still fresh."""
    found = _CACHE.get(key)
    if found is None:
        return None
    expires, jobs = found
    if expires <= now:
        _CACHE.pop(key, None)
        return None
    return list(jobs)


def remember(key: tuple, jobs: list, now: datetime) -> None:
    """Keep one successful response briefly so the same search is not repeated."""
    _CACHE[key] = (now + timedelta(seconds=CACHE_SECONDS), list(jobs))


def reserve(country: str, now: datetime, limit: int = DAILY_SAFETY_LIMIT) -> bool:
    """Record one outbound request. False means today's safety limit is already used."""
    day = now.astimezone(timezone.utc).date()
    key = (country, day)
    used = _COUNTS.get(key, 0)
    if used >= limit:
        return False
    _COUNTS[key] = used + 1
    return True
