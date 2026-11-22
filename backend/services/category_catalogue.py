"""Cache the official Adzuna category catalogue.

The cache keeps the labels and tags returned for each configured country.
It does not invent categories and it does not write to the database.
"""

import time

from services.adzuna import AdzunaError, AdzunaSource
from services.job_discovery import _safe_message
from services.search_catalog import DEFAULT_DISCOVERY_COUNTRIES

CACHE_SECONDS = 60 * 60
ERROR_CACHE_SECONDS = 60
_CACHE = {"expires": 0.0, "categories": None, "error": None}


def cached_categories(*, source=None, sleep=time.sleep, now=None, ttl: int = CACHE_SECONDS, countries=None):
    """Return the cached catalogue, fetching it at most once per ttl."""
    clock = time.time if now is None else now
    current = clock() if callable(clock) else clock
    if _CACHE["categories"] is not None and current < _CACHE["expires"]:
        return list(_CACHE["categories"]), _CACHE["error"]
    provider = source or AdzunaSource()
    codes = tuple(countries or DEFAULT_DISCOVERY_COUNTRIES)
    found = []
    errors = []
    for index, country in enumerate(codes):
        if index and sleep is not None:
            sleep(1.0)
        try:
            rows = list(provider.list_categories(country=country))
        except AdzunaError as exc:
            errors.append(_safe_message(str(exc)))
            continue
        except Exception:
            errors.append("The Adzuna request could not be completed.")
            continue
        for item in rows:
            found.append({"country": item.country, "label": item.label, "tag": item.tag})
    error = " ".join(errors) if errors else None
    _CACHE["categories"] = found
    _CACHE["error"] = error
    _CACHE["expires"] = current + (ttl if found else ERROR_CACHE_SECONDS)
    return list(found), error


def clear_category_cache() -> None:
    """Drop the cached catalogue. Tests use this so one case cannot leak into the next."""
    _CACHE["expires"] = 0.0
    _CACHE["categories"] = None
    _CACHE["error"] = None
