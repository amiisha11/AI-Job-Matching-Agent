"""Insert or update Adzuna listings without touching manually seeded jobs.

A dry run classifies rows and does not commit. A failed search does not
change job rows. Credentials are removed from any stored error message.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Job, JobSyncLog
from services.adzuna import AdzunaError, AdzunaJob, search_jobs
from services.job_discovery import DiscoverySummary, DiscoveredJob
from settings import get_adzuna_app_id, get_adzuna_app_key

PROVIDER = "adzuna"
MAX_IMPORT = 50
UNMATCHABLE_REASON = "Required skills were not supplied by the provider."
_SAFE_FAILURE = "The Adzuna request could not be completed."


@dataclass(frozen=True)
class NormalizedListing:
    """One provider listing mapped onto the existing job columns."""

    source: str
    external_job_id: str
    source_country: str
    title: str
    company: str
    location: str
    description: str | None
    source_url: str | None
    posted_at: datetime | None


@dataclass(frozen=True)
class ImportSummary:
    """Counts for one import attempt. `wrote` is true only after a commit."""

    status: str
    country: str
    query: str
    fetched: int
    ready: int
    skipped: int
    inserted: int
    updated: int
    wrote: bool
    error_message: str | None
    jobs: tuple[NormalizedListing, ...]


@dataclass(frozen=True)
class CatalogueSummary:
    """The bulk plan. Job rows are written only when `wrote` is true."""

    status: str
    insertable: int
    updated: int
    duplicates_skipped: int
    identity_conflicts: int
    unmatchable: int
    wrote: bool
    logs_written: bool
    compared: bool
    error_message: str | None


def import_catalogue(
    summary: DiscoverySummary,
    *,
    session: Session | None,
    commit: bool,
    known_keys: set[tuple[str, str, str]] | None = None,
    now=None,
) -> CatalogueSummary:
    """Store the already deduplicated catalogue. Dry-run only classifies it.

    Listings that share a provider id but were kept separate cannot both be
    stored: the database allows one row per source, country, and external id.
    The first copy is the one that would be saved. Manual jobs are never matched.
    """
    if commit and session is None:
        raise RuntimeError("Commit mode needs a database session.")
    started = _now(now)
    known = set(known_keys or ())
    compared = known_keys is not None or session is not None
    ready, inserts, updates, conflicts = _attribute(summary.jobs, known)
    duplicates = summary.cross_query_duplicates + conflicts
    if not commit:
        if session is not None:
            session.rollback()
        return _catalogue_result(
            summary,
            inserts,
            updates,
            duplicates,
            conflicts,
            wrote=False,
            logs_written=False,
            compared=compared,
            error_message=None,
        )

    try:
        rows = _existing_external(session, _catalogue_items(summary.jobs))
        known = set(rows)
        ready, inserts, updates, conflicts = _attribute(summary.jobs, known)
        duplicates = summary.cross_query_duplicates + conflicts
        for item in ready:
            current = rows.get((item.source, item.source_country, item.external_job_id))
            if current is None:
                session.add(_new_job(item, started))
            else:
                _update_job(current, item, started)
        _record_logs(session, summary, inserts, updates, started, rolled_back=False)
        session.commit()
        job_changes = sum(inserts.values()) + sum(updates.values())
    except Exception:
        session.rollback()
        logs_written = _record_rollback(session, summary, started)
        return _catalogue_result(
            summary,
            inserts,
            updates,
            duplicates,
            conflicts,
            wrote=False,
            logs_written=logs_written,
            compared=True,
            error_message=_SAFE_FAILURE,
        )
    return _catalogue_result(
        summary,
        inserts,
        updates,
        duplicates,
        conflicts,
        wrote=job_changes > 0,
        logs_written=bool(summary.attempts),
        compared=True,
        error_message=None,
    )


def import_adzuna_jobs(
    *,
    country: str,
    what: str,
    limit: int,
    commit: bool,
    session: Session | None = None,
    search=search_jobs,
    now=None,
) -> ImportSummary:
    """Fetch one page and, only when commit is true, upsert those listings."""
    started = _now(now)
    country_code = str(country or "").strip().lower()
    query = " ".join(str(what or "").split())
    page_size = _limit(limit)
    if commit and session is None:
        raise RuntimeError("Commit mode needs a database session.")

    try:
        result = search(country=country_code, page=1, what=query, results_per_page=page_size)
        listings = list(result.jobs)
    except AdzunaError as exc:
        return _finish_error(session, commit, country_code, query, started, _safe_message(str(exc)), now)
    except Exception:
        return _finish_error(session, commit, country_code, query, started, _SAFE_FAILURE, now)

    ready, skipped = _normalize(listings, country_code)
    if session is None:
        inserted, updated = 0, 0
    else:
        known = _existing_ids(session, country_code, ready)
        inserted, updated = _classify(ready, known, session, commit, _now(now))
    if commit:
        _add_log(
            session,
            country=country_code,
            query=query,
            started=started,
            completed=_now(now),
            fetched=len(listings),
            inserted=inserted,
            updated=updated,
            skipped=skipped,
            status="success",
            error_message=None,
        )
        session.commit()
    elif session is not None:
        session.rollback()
    return ImportSummary(
        status="success",
        country=country_code,
        query=query,
        fetched=len(listings),
        ready=len(ready),
        skipped=skipped,
        inserted=inserted,
        updated=updated,
        wrote=commit,
        error_message=None,
        jobs=tuple(ready),
    )


def _finish_error(session, commit: bool, country: str, query: str, started: datetime, message: str, now) -> ImportSummary:
    """Record a failed search without updating job rows."""
    wrote = False
    if commit and session is not None:
        session.rollback()
        _add_log(
            session,
            country=country,
            query=query,
            started=started,
            completed=_now(now),
            fetched=0,
            inserted=0,
            updated=0,
            skipped=0,
            status="error",
            error_message=message,
        )
        session.commit()
        wrote = True
    elif session is not None:
        session.rollback()
    return ImportSummary(
        status="error",
        country=country,
        query=query,
        fetched=0,
        ready=0,
        skipped=0,
        inserted=0,
        updated=0,
        wrote=wrote,
        error_message=message,
        jobs=(),
    )


def _normalize(listings: list[AdzunaJob], country: str) -> tuple[list[NormalizedListing], int]:
    ready: list[NormalizedListing] = []
    seen: set[str] = set()
    skipped = 0
    for listing in listings:
        item = _one_listing(listing, country)
        if item is None or item.external_job_id in seen:
            skipped += 1
            continue
        seen.add(item.external_job_id)
        ready.append(item)
    return ready, skipped


def _one_listing(listing: AdzunaJob, country: str) -> NormalizedListing | None:
    external_id = _clip(listing.external_id or "", 80)
    title = _clip(listing.title, 500)
    company = _clip(listing.company, 500)
    location = _clip(listing.location, 500)
    if not external_id or not title or not company or not location:
        return None
    description = listing.description.strip() if isinstance(listing.description, str) else None
    return NormalizedListing(
        source=PROVIDER,
        external_job_id=external_id,
        source_country=country,
        title=title,
        company=company,
        location=location,
        description=description or None,
        source_url=listing.redirect_url,
        posted_at=_posted_at(listing.created),
    )


def _catalogue_result(
    summary: DiscoverySummary,
    inserts: dict[tuple[str, str], int],
    updates: dict[tuple[str, str], int],
    duplicates: int,
    conflicts: int,
    *,
    wrote: bool,
    logs_written: bool,
    compared: bool,
    error_message: str | None,
) -> CatalogueSummary:
    insertable = sum(inserts.values())
    updated = sum(updates.values())
    status = "error" if error_message or not summary.requests_succeeded else "success"
    return CatalogueSummary(
        status=status,
        insertable=insertable,
        updated=updated,
        duplicates_skipped=duplicates,
        identity_conflicts=conflicts,
        unmatchable=insertable + updated,
        wrote=wrote,
        logs_written=logs_written,
        compared=compared,
        error_message=error_message,
    )


def _catalogue_items(jobs: tuple[DiscoveredJob, ...]) -> list[NormalizedListing]:
    ready, _inserts, _updates, _conflicts = _attribute(jobs, set())
    return ready


def _attribute(
    jobs: tuple[DiscoveredJob, ...],
    known: set[tuple[str, str, str]],
) -> tuple[list[NormalizedListing], dict[tuple[str, str], int], dict[tuple[str, str], int], int]:
    """Keep the first copy of each provider identity and count the rest as conflicts."""
    ready: list[NormalizedListing] = []
    inserts: dict[tuple[str, str], int] = {}
    updates: dict[tuple[str, str], int] = {}
    seen: set[tuple[str, str, str]] = set()
    conflicts = 0
    for job in jobs:
        identity = (job.source, job.country, job.external_job_id)
        if identity in seen:
            conflicts += 1
            continue
        seen.add(identity)
        ready.append(_from_discovered(job))
        owner = (job.country, job.queries[0] if job.queries else "")
        bucket = updates if identity in known else inserts
        bucket[owner] = bucket.get(owner, 0) + 1
    return ready, inserts, updates, conflicts


def _from_discovered(job: DiscoveredJob) -> NormalizedListing:
    """Copy the fields the dry-run already normalized. Nothing new is invented."""
    return NormalizedListing(
        source=job.source,
        external_job_id=job.external_job_id,
        source_country=job.country,
        title=job.title,
        company=job.company,
        location=job.location,
        description=job.description,
        source_url=job.source_url,
        posted_at=job.posted_at,
    )


def _existing_external(session: Session, ready: list[NormalizedListing]) -> dict[tuple[str, str, str], Job]:
    """Find Adzuna rows only. A manual job has no source, so it cannot match."""
    if not ready:
        return {}
    identifiers = [item.external_job_id for item in ready]
    rows = session.scalars(
        select(Job).where(
            Job.source == PROVIDER,
            Job.external_job_id.in_(identifiers),
        )
    )
    return {
        (row.source, row.source_country, row.external_job_id): row
        for row in rows
        if row.source and row.source_country and row.external_job_id
    }


def _record_logs(session, summary: DiscoverySummary, inserts, updates, started, *, rolled_back: bool) -> None:
    completed = _now(None)
    for attempt in summary.attempts:
        owner = (attempt.country, attempt.query)
        if attempt.status == "error":
            _add_log(
                session,
                country=attempt.country,
                query=attempt.query,
                started=completed,
                completed=completed,
                fetched=0,
                inserted=0,
                updated=0,
                skipped=0,
                status="error",
                error_message=attempt.error_message or _SAFE_FAILURE,
            )
            continue
        if rolled_back:
            _add_log(
                session,
                country=attempt.country,
                query=attempt.query,
                started=started,
                completed=completed,
                fetched=0,
                inserted=0,
                updated=0,
                skipped=0,
                status="error",
                error_message="The import was rolled back. No listings were changed.",
            )
            continue
        inserted = inserts.get(owner, 0)
        updated = updates.get(owner, 0)
        skipped = attempt.fetched - inserted - updated
        _add_log(
            session,
            country=attempt.country,
            query=attempt.query,
            started=started,
            completed=completed,
            fetched=attempt.fetched,
            inserted=inserted,
            updated=updated,
            skipped=max(skipped, 0),
            status="success",
            error_message=None,
        )


def _record_rollback(session, summary: DiscoverySummary, started) -> bool:
    """Store error logs only after the job changes have been discarded."""
    try:
        _record_logs(session, summary, {}, {}, started, rolled_back=True)
        session.commit()
    except Exception:
        session.rollback()
        return False
    return True


def _existing_ids(session: Session | None, country: str, ready: list[NormalizedListing]) -> dict[str, Job]:
    if session is None or not ready:
        return {}
    identifiers = [item.external_job_id for item in ready]
    rows = session.scalars(
        select(Job).where(
            Job.source == PROVIDER,
            Job.source_country == country,
            Job.external_job_id.in_(identifiers),
        )
    )
    return {row.external_job_id: row for row in rows if row.external_job_id}


def _classify(ready, known: dict[str, Job], session: Session | None, commit: bool, seen_at: datetime) -> tuple[int, int]:
    inserted = 0
    updated = 0
    for item in ready:
        current = known.get(item.external_job_id)
        if current is None:
            inserted += 1
            if commit and session is not None:
                session.add(_new_job(item, seen_at))
            continue
        updated += 1
        if commit:
            _update_job(current, item, seen_at)
    return inserted, updated


def _new_job(item: NormalizedListing, seen_at: datetime) -> Job:
    return Job(
        title=item.title,
        company=item.company,
        location=item.location,
        description=item.description,
        required_skills=[],
        min_experience=0,
        source=item.source,
        external_job_id=item.external_job_id,
        source_country=item.source_country,
        source_url=item.source_url,
        posted_at=item.posted_at,
        last_synced_at=seen_at,
        last_seen_at=seen_at,
        is_active=True,
        **_unmatchable_fields(item),
    )


def _update_job(job: Job, item: NormalizedListing, seen_at: datetime) -> None:
    """Refresh provider fields. The primary key and saved-job links stay put."""
    job.title = item.title
    job.company = item.company
    job.location = item.location
    job.description = item.description
    job.source_url = item.source_url
    job.posted_at = item.posted_at
    job.last_synced_at = seen_at
    job.last_seen_at = seen_at
    job.is_active = True
    for name, value in _unmatchable_fields(item).items():
        setattr(job, name, value)


def _unmatchable_fields(item: NormalizedListing) -> dict:
    """External listings stay unscored until the provider supplies skill requirements."""
    snippet = bool(item.description)
    return {
        "is_matchable": False,
        "matchability_status": "unmatchable",
        "matchability_reason": UNMATCHABLE_REASON,
        "description_is_snippet": snippet,
        "requirements_available": False,
    }


def _add_log(session: Session, **values) -> None:
    session.add(
        JobSyncLog(
            provider=PROVIDER,
            country=_clip(values["country"], 2),
            search_query=_clip(values["query"], 200),
            started_at=values["started"],
            completed_at=values["completed"],
            fetched_count=values["fetched"],
            inserted_count=values["inserted"],
            updated_count=values["updated"],
            skipped_count=values["skipped"],
            status=values["status"],
            error_message=values["error_message"],
        )
    )


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


def _limit(limit: int) -> int:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_IMPORT:
        raise RuntimeError(f"The import limit must be a whole number from 1 to {MAX_IMPORT}.")
    return limit


def _clip(value: str, limit: int) -> str:
    cleaned = " ".join(str(value or "").split())
    return cleaned[:limit]


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
