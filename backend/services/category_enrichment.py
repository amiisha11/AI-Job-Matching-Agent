"""Match category-search listings to stored Adzuna rows.

Identity is source, country, and external id. A category is copied only from
the provider payload. Titles are not classified, and nothing is written unless
the caller later commits on a database that already has the category columns.
"""

from dataclasses import dataclass, replace

from sqlalchemy import text

from services.job_discovery import DiscoveredJob
from services.job_import import _from_discovered, _new_job, _now

PROVIDER = "adzuna"


@dataclass(frozen=True)
class StoredIdentity:
    """One stored Adzuna listing, without its description or URL."""

    source: str
    country: str
    external_job_id: str
    category_label: str | None = None
    category_tag: str | None = None
    is_matchable: bool = False


@dataclass(frozen=True)
class CategoryAction:
    """One planned change. Enrichment never replaces a different stored tag."""

    kind: str
    source: str
    country: str
    external_job_id: str
    category_label: str | None
    category_tag: str | None
    job: DiscoveredJob | None = None


@dataclass(frozen=True)
class EnrichmentPlan:
    """Counts for one comparison. `wrote` is true only after a commit."""

    actions: tuple[CategoryAction, ...]
    catalogue: tuple[tuple[str, str, str], ...]
    matched: int
    enrichable: int
    already_categorised: int
    category_conflicts: int
    insertable: int
    duplicates: int
    missing_category: int
    missing_skills: int
    stored_adzuna: int
    stored_unmatched: int
    by_country: dict[str, dict[str, int]]
    by_category: dict[str, dict[str, int]]
    wrote: bool = False


def plan_category_enrichment(jobs, stored, *, catalogue=()) -> EnrichmentPlan:
    """Classify listings. The same provider id in another country stays a new row."""
    index = {
        (row.source, row.country.strip().lower(), row.external_job_id): row
        for row in stored
        if row.source and row.country and row.external_job_id
    }
    seen: set[tuple[str, str, str]] = set()
    actions: list[CategoryAction] = []
    duplicates = 0
    missing_category = 0
    by_country: dict[str, dict[str, int]] = {}
    by_category: dict[str, dict[str, int]] = {}
    for job in jobs:
        identity = (job.source, str(job.country or "").strip().lower(), job.external_job_id)
        if not identity[1] or not identity[2]:
            continue
        if identity in seen:
            duplicates += 1
            continue
        seen.add(identity)
        label, tag = _category(job)
        if not tag:
            missing_category += 1
        current = index.get(identity)
        action = _action(job, identity, label, tag, current)
        actions.append(action)
        _count(by_country, identity[1], action.kind)
        _count(by_category, label or "Not supplied", action.kind)
    matched_keys = {
        (action.source, action.country, action.external_job_id)
        for action in actions
        if action.kind != "insert"
    }
    return EnrichmentPlan(
        actions=tuple(actions),
        catalogue=_catalogue_rows(catalogue),
        matched=len(matched_keys),
        enrichable=sum(action.kind == "enrich" for action in actions),
        already_categorised=sum(action.kind == "keep" for action in actions),
        category_conflicts=sum(action.kind == "conflict" for action in actions),
        insertable=sum(action.kind == "insert" for action in actions),
        duplicates=duplicates,
        missing_category=missing_category,
        missing_skills=len(actions),
        stored_adzuna=len(index),
        stored_unmatched=len(set(index) - matched_keys),
        by_country=by_country,
        by_category=by_category,
    )


def read_stored_identities(connection) -> tuple[list[StoredIdentity], dict]:
    """Read Adzuna identities. The caller rolls back; this function does not write."""
    columns = _column_names(connection)
    has_category = "category_label" in columns and "category_tag" in columns
    category_sql = ", category_label, category_tag" if has_category else ""
    rows = connection.execute(
        text(
            "SELECT source, source_country, external_job_id, is_matchable"
            f"{category_sql} FROM jobs "
            "WHERE source = :source AND external_job_id IS NOT NULL"
        ),
        {"source": PROVIDER},
    )
    identities = []
    for row in rows:
        mapping = row._mapping
        identities.append(
            StoredIdentity(
                source=mapping["source"],
                country=str(mapping["source_country"] or ""),
                external_job_id=str(mapping["external_job_id"]),
                category_label=mapping["category_label"] if has_category else None,
                category_tag=mapping["category_tag"] if has_category else None,
                is_matchable=bool(mapping["is_matchable"]),
            )
        )
    stats = {
        "jobs": _count_sql(connection, "SELECT COUNT(*) FROM jobs"),
        "manual_jobs": _count_sql(connection, "SELECT COUNT(*) FROM jobs WHERE source IS NULL"),
        "saved_jobs": _count_sql(connection, "SELECT COUNT(*) FROM saved_jobs"),
        "adzuna_jobs": len(identities),
        "adzuna_unmatchable": sum(not row.is_matchable for row in identities),
        "category_columns": has_category,
        "category_table": _table_exists(connection, "provider_categories"),
    }
    return identities, stats


def apply_category_plan(session, jobs, *, catalogue=(), commit: bool, now=None):
    """Commit category changes only. Other stored fields and saved jobs stay put."""
    identities, stats = read_stored_identities(session.connection())
    plan = plan_category_enrichment(jobs, identities, catalogue=catalogue)
    if not commit:
        session.rollback()
        return plan
    if not stats["category_columns"]:
        session.rollback()
        raise RuntimeError("Category columns are not ready. Run the category migration before commit.")
    started = _now(now)
    for action in plan.actions:
        if action.kind == "insert" and action.job is not None:
            session.add(_new_job(_from_discovered(action.job), started))
    session.flush()
    for action in plan.actions:
        if action.kind not in {"enrich", "insert"} or not action.category_tag:
            continue
        session.execute(
            text(
                "UPDATE jobs SET category_label = :label, category_tag = :tag "
                "WHERE source = :source AND source_country = :country AND external_job_id = :external_job_id "
                "AND (category_tag IS NULL OR category_tag = '' OR category_tag = :tag)"
            ),
            {
                "label": action.category_label,
                "tag": action.category_tag,
                "source": action.source,
                "country": action.country,
                "external_job_id": action.external_job_id,
            },
        )
    if stats["category_table"]:
        for country, tag, label in plan.catalogue:
            session.execute(
                text(
                    "INSERT INTO provider_categories (country, tag, label) VALUES (:country, :tag, :label) "
                    "ON CONFLICT (country, tag) DO NOTHING"
                ),
                {"country": country, "tag": tag, "label": label},
            )
    session.commit()
    return replace(plan, wrote=True)


def _action(job: DiscoveredJob, identity, label: str, tag: str, current: StoredIdentity | None) -> CategoryAction:
    source, country, external_id = identity
    if current is None:
        return CategoryAction("insert", source, country, external_id, label or None, tag or None, job)
    stored_tag = " ".join(str(current.category_tag or "").split())
    if stored_tag and tag and stored_tag != tag:
        return CategoryAction("conflict", source, country, external_id, current.category_label, stored_tag, job)
    if stored_tag:
        return CategoryAction("keep", source, country, external_id, current.category_label or label, stored_tag, job)
    if not tag:
        return CategoryAction("uncategorised", source, country, external_id, None, None, job)
    return CategoryAction("enrich", source, country, external_id, label, tag, job)


def _category(job: DiscoveredJob) -> tuple[str, str]:
    label = " ".join(str(job.category_label or "").split())
    tag = " ".join(str(job.category_tag or "").split())
    return label, tag


def _catalogue_rows(categories) -> tuple[tuple[str, str, str], ...]:
    seen: set[tuple[str, str]] = set()
    rows = []
    for item in categories:
        country = " ".join(str(getattr(item, "country", "") or "").split()).lower()
        tag = " ".join(str(getattr(item, "tag", "") or "").split())
        label = " ".join(str(getattr(item, "label", "") or "").split())
        if isinstance(item, dict):
            country = " ".join(str(item.get("country") or "").split()).lower()
            tag = " ".join(str(item.get("tag") or "").split())
            label = " ".join(str(item.get("label") or "").split())
        key = (country, tag)
        if not country or not tag or not label or key in seen:
            continue
        seen.add(key)
        rows.append((country, tag, label))
    return tuple(rows)


def _count(bucket: dict[str, dict[str, int]], key: str, kind: str) -> None:
    counts = bucket.setdefault(key, {"enrich": 0, "insert": 0, "keep": 0, "conflict": 0, "uncategorised": 0})
    counts[kind] = counts.get(kind, 0) + 1


def _column_names(connection) -> set[str]:
    dialect = connection.dialect.name
    if dialect == "sqlite":
        return {row[1] for row in connection.execute(text("PRAGMA table_info(jobs)"))}
    rows = connection.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'jobs'"
        )
    )
    return {row[0] for row in rows}


def _table_exists(connection, name: str) -> bool:
    if connection.dialect.name == "sqlite":
        row = connection.execute(
            text("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = :name"),
            {"name": name},
        ).first()
        return row is not None
    row = connection.execute(
        text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = :name"
        ),
        {"name": name},
    ).first()
    return row is not None


def _count_sql(connection, statement: str) -> int:
    value = connection.execute(text(statement)).scalar()
    return int(value or 0)
