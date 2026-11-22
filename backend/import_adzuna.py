"""Import Adzuna listings. Writes happen only with --commit.

Preview the configured UK and India catalogue, from the project root:

    .\\.venv\\Scripts\\python.exe backend\\import_adzuna.py --countries gb in --use-catalog --limit-per-query 3 --sort-by date --dry-run

Commit that same catalogue after the migration:

    .\\.venv\\Scripts\\python.exe backend\\import_adzuna.py --countries gb in --use-catalog --limit-per-query 3 --sort-by date --commit

One search stays available too:

    .\\.venv\\Scripts\\python.exe backend\\import_adzuna.py --country gb --what "Python Developer" --limit 5 --dry-run

The migration that adds the source columns is separate:

    .\\.venv\\Scripts\\python.exe backend\\migrate_job_source.py
"""

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.category_enrichment import apply_category_plan, plan_category_enrichment, read_stored_identities
from services.job_discovery import (
    DiscoverySummary,
    collect_categories,
    discover_categories,
    discover_jobs,
    sample_categories,
)
from services.job_import import CatalogueSummary, ImportSummary, import_adzuna_jobs, import_catalogue
from services.search_catalog import COUNTRY_NAMES, DEFAULT_DISCOVERY_COUNTRIES, ROLE_SEARCHES, RoleSearch


def main(argv: list[str] | None = None) -> int:
    """Fetch listings and print a safe summary. Commit is never the default."""
    _configure_output()
    args = _parser().parse_args(argv)
    if args.use_categories:
        return _run_categories(args)
    if _discovery_requested(args):
        return _run_catalogue(args)
    session = None
    if args.commit:
        from database import SessionLocal

        session = SessionLocal()
    try:
        summary = import_adzuna_jobs(
            country=args.country,
            what=args.what,
            limit=args.limit,
            commit=args.commit,
            session=session,
        )
    except Exception:
        print("Import status: failed")
        print("Database writes: none")
        print("Error: The Adzuna request could not be completed.")
        return 1
    finally:
        if session is not None:
            session.close()
    _print_summary(summary, args.commit)
    return 0 if summary.status == "success" else 1


def _configure_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            continue


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import Adzuna jobs without printing credentials.")
    parser.add_argument("--country", default="gb")
    parser.add_argument("--what", default="Python Developer")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--countries", nargs="+")
    parser.add_argument("--queries", nargs="+")
    parser.add_argument("--limit-per-query", type=int)
    parser.add_argument("--sort-by", choices=("date", "salary", "relevance"))
    parser.add_argument("--use-catalog", action="store_true")
    parser.add_argument("--use-categories", action="store_true")
    parser.add_argument("--enrich-stored", action="store_true")
    parser.add_argument("--sample-per-country", type=int, default=0)
    parser.add_argument("--pages", type=int, default=1)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--commit", action="store_true")
    return parser


def _run_categories(args) -> int:
    """Read official categories and optionally sample them. This path never writes."""
    if args.commit and not args.enrich_stored:
        print("Import status: failed")
        print("Mode: commit")
        print("Database writes: none")
        print("Error: Category discovery is dry-run only. Remove --commit.")
        return 2
    if args.commit and args.enrich_stored and not _category_columns_ready():
        print("Import status: failed")
        print("Mode: commit")
        print("Database writes: none")
        print("Error: Category columns are not ready. Run backend\\migrate_job_categories.py before --commit.")
        return 2
    if args.use_catalog or args.queries:
        print("Import status: failed")
        print("Database writes: none")
        print("Error: Use --use-categories on its own, without --use-catalog or --queries.")
        return 2
    limit = args.limit_per_query if args.limit_per_query is not None else 2
    print("Coverage: the countries named for this run only. This is not a worldwide search.")
    print(
        f"Request budget: one category catalogue per country, then one search per returned category "
        f"unless a sample size is set. Limit {limit} listing(s), {args.pages} page(s), newest first."
    )
    print(
        "Spacing: 1.0 seconds between requests. HTTP 429 waits 1 second and then 2 seconds across two retries. "
        "Three categories in a row that stay limited stop the remaining searches."
    )
    try:
        countries = _countries(args)
        categories, catalogue_attempts = collect_categories(countries, pause_seconds=1.0)
        chosen = []
        for country in countries:
            rows = [item for item in categories if item.country == country]
            if args.sample_per_country:
                chosen.extend(sample_categories(rows, args.sample_per_country))
            else:
                chosen.extend(rows)
        summary = None
        print(f"Categories selected: {len(chosen)}")
        print(f"Planned search requests: {len(chosen) * args.pages}")
        if chosen:
            summary = discover_categories(
                countries=countries,
                categories=chosen,
                limit=limit,
                pages=args.pages,
                sort_by=args.sort_by or "date",
                pause_seconds=1.0,
            )
    except RuntimeError as exc:
        print("Import status: failed")
        print("Database writes: none")
        print(f"Error: {exc}")
        return 2
    except Exception:
        print("Import status: failed")
        print("Database writes: none")
        print("Error: The Adzuna request could not be completed.")
        return 1
    _print_categories(countries, categories, catalogue_attempts, summary, bool(args.sample_per_country))
    if args.enrich_stored and summary is not None:
        _report_enrichment(summary.jobs, categories, commit=bool(args.commit))
    catalogue_ok = any(item.status == "success" for item in catalogue_attempts)
    search_ok = summary is None or bool(summary.requests_succeeded) or summary.requests_attempted == 0
    return 0 if catalogue_ok and search_ok else 1


def _print_categories(countries, categories, attempts, summary, sampled: bool) -> None:
    print("Import status: success" if categories or any(item.status == "success" for item in attempts) else "Import status: failed")
    print("Mode: dry-run")
    print("Database writes: none")
    print(f"Category requests: {len(attempts)}")
    print(f"Category requests failed: {sum(item.status == 'error' for item in attempts)}")
    for country in countries:
        rows = [item for item in categories if item.country == country]
        print(f"Categories for {country}: {len(rows)}")
        for item in rows:
            print(f"  {item.country} | {item.label} | {item.tag}")
    for attempt in attempts:
        if attempt.status == "error":
            print(
                f"Failed category catalogue: {_country_name(attempt.country)} / "
                f"HTTP {attempt.status_code if attempt.status_code is not None else 'unavailable'} / "
                f"{attempt.error_message}"
            )
    if summary is None:
        print("Category searches: 0")
        return
    print("Category search scope: " + ("sample" if sampled else "every returned category"))
    print(f"Search requests attempted: {summary.requests_attempted}")
    print(f"Search requests succeeded: {summary.requests_succeeded}")
    print(f"Search requests failed: {summary.requests_failed}")
    print(f"HTTP search calls: {summary.http_requests}")
    print(f"Fetched: {summary.fetched}")
    print(f"Unique listings: {summary.unique}")
    print(f"Unique by source, country, and external id: {summary.unique - summary.kept_separate}")
    print(f"Duplicates across categories: {summary.cross_query_duplicates}")
    print(f"Same source id kept separate: {summary.kept_separate}")
    print("Listings by country: " + ", ".join(f"{_country_name(code)} {count}" for code, count in summary.by_country.items()))
    print("Results by category:")
    empty = 0
    for attempt in summary.attempts:
        state = attempt.status
        if attempt.status == "success" and attempt.fetched == 0:
            state = "empty"
            empty += 1
        print(
            f"  {attempt.country} | {attempt.category} | {attempt.query} | "
            f"fetched {attempt.fetched} | {state}"
        )
    print(f"Empty categories: {empty}")
    print(f"Categories that failed: {summary.requests_failed}")
    stopped = sum(item.status == "stopped" for item in summary.attempts)
    print(f"Categories stopped after rate limits: {stopped}")
    missing_links = sum(not job.source_url for job in summary.jobs)
    supplied_salary = sum(job.salary_status == "supplied" for job in summary.jobs)
    supplied_currency = sum(job.salary_currency is not None for job in summary.jobs)
    predicted = sum(job.salary_status == "predicted figure ignored" for job in summary.jobs)
    print(f"Missing descriptions: {summary.missing_descriptions}")
    print(f"Description snippets: {summary.incomplete_descriptions - summary.missing_descriptions}")
    print(f"Missing required skills: {summary.missing_required_skills}")
    print(f"Missing application links: {missing_links}")
    print(f"Older than 30 days: {summary.old_listings}")
    print(f"Posting date not supplied: {summary.undated_listings}")
    print(f"Salary supplied: {supplied_salary}")
    print(f"Salary currency supplied: {supplied_currency}")
    print(f"Predicted salaries ignored: {predicted}")
    print(f"Employment type supplied: {sum(bool(job.contract_type) for job in summary.jobs)}")
    print(f"Hours supplied: {sum(bool(job.contract_time) for job in summary.jobs)}")
    print(f"Workplace supplied: {sum(bool(job.workplace) for job in summary.jobs)}")
    print("Matchable listings: 0")
    print(f"Unmatchable listings: {summary.unique}")
    print("Matchability: unmatchable until the provider supplies structured required skills.")
    for attempt in summary.attempts:
        if attempt.status == "error":
            print(
                f"Failed category search: {_country_name(attempt.country)} / {attempt.category} / {attempt.query} / "
                f"HTTP {attempt.status_code if attempt.status_code is not None else 'unavailable'} / "
                f"{attempt.error_message}"
            )
    shown: dict[str, int] = {}
    for job in summary.jobs:
        label = job.category_label or (job.categories[0] if job.categories else "")
        if shown.get(label, 0) >= 1:
            continue
        if len(shown) >= 8:
            break
        shown[label] = shown.get(label, 0) + 1
        print(f"- Title: {job.title}")
        print(f"  Company: {job.company}")
        print(f"  Location: {job.location}")
        print(f"  Country: {_country_name(job.country)} ({job.country})")
        print(f"  Category: {label}")
        print(f"  Category tag: {job.category_tag or 'not supplied'}")
        print(f"  Link supplied: {'yes' if job.source_url else 'no'}")
        print("  Required skills: not supplied by Adzuna")


def _category_columns_ready() -> bool:
    """Read whether the category columns exist. A failure is treated as not ready."""
    try:
        _identities, stats = _read_enrichment_state()
    except Exception:
        return False
    return bool(stats.get("category_columns"))


def _read_enrichment_state():
    """Read stored identities, then roll the transaction back."""
    from database import engine

    with engine.connect() as connection:
        try:
            return read_stored_identities(connection)
        finally:
            connection.rollback()


def _report_enrichment(jobs, categories, *, commit: bool) -> None:
    if commit:
        from database import SessionLocal

        session = SessionLocal()
        try:
            plan = apply_category_plan(session, jobs, catalogue=categories, commit=True)
            _print_enrichment(plan, {"jobs": None, "manual_jobs": None, "adzuna_jobs": plan.stored_adzuna, "adzuna_unmatchable": None, "saved_jobs": None, "category_columns": True})
        finally:
            session.close()
        return
    try:
        identities, stats = _read_enrichment_state()
    except Exception:
        print("Enrichment comparison: unavailable")
        print("Database writes: none")
        print("Error: Stored Adzuna identities could not be read.")
        return
    plan = plan_category_enrichment(jobs, identities, catalogue=categories)
    _print_enrichment(plan, stats)


def _print_enrichment(plan, stats: dict) -> None:
    print("Enrichment comparison: " + ("committed" if plan.wrote else "read-only"))
    print(f"Database writes: {'committed' if plan.wrote else 'none'}")
    print(f"Stored jobs: {_count(stats.get('jobs'))}")
    print(f"Manually seeded jobs: {_count(stats.get('manual_jobs'))}")
    print(f"Stored Adzuna jobs: {_count(stats.get('adzuna_jobs'))}")
    print(f"Stored Adzuna jobs that are unmatchable: {_count(stats.get('adzuna_unmatchable'))}")
    print(f"Saved jobs: {_count(stats.get('saved_jobs'))}")
    print(f"Category columns present: {'yes' if stats.get('category_columns') else 'no'}")
    supplied = sum(1 for action in plan.actions if action.kind in {"enrich", "conflict"} or (action.kind == "keep" and action.category_tag))
    print(f"Existing Adzuna records matched: {plan.matched}")
    print(f"Existing records with category metadata available: {supplied}")
    print(f"Existing records that could be enriched: {plan.enrichable}")
    print(f"Existing records that already have this category: {plan.already_categorised}")
    print(f"Existing records left unchanged because the stored category differs: {plan.category_conflicts}")
    print(f"Existing Adzuna records not in this snapshot: {plan.stored_unmatched}")
    print(f"New unique listings to insert: {plan.insertable}")
    print(f"Duplicates skipped: {plan.duplicates}")
    print(f"Discovered listings missing a category: {plan.missing_category}")
    print(f"Discovered listings missing required skills: {plan.missing_skills}")
    print(f"Provider category rows that would be stored: {len(plan.catalogue)}")
    print("Matchability changes: 0")
    for country, counts in plan.by_country.items():
        print(
            f"  {country}: enrich {counts.get('enrich', 0)}, insert {counts.get('insert', 0)}, "
            f"unchanged {counts.get('keep', 0) + counts.get('conflict', 0) + counts.get('uncategorised', 0)}"
        )
    for label, counts in plan.by_category.items():
        print(f"  {label}: enrich {counts.get('enrich', 0)}, insert {counts.get('insert', 0)}")


def _discovery_requested(args) -> bool:
    return bool(args.countries or args.queries or args.use_catalog)


def _run_catalogue(args) -> int:
    """Search the catalogue, then classify or commit that same result."""
    state = _read_catalogue_state()
    if args.commit and not state["schema_ready"]:
        print("Import status: failed")
        print("Mode: commit")
        print("Database writes: none")
        print("Error: Job source columns are not ready. Run the migration before commit.")
        return 2
    try:
        countries = _countries(args)
        searches = _searches(args)
        limit = args.limit_per_query if args.limit_per_query is not None else 3
        summary = discover_jobs(
            countries=countries,
            searches=searches,
            limit=limit,
            sort_by=args.sort_by or "date",
            pause_seconds=1.0,
        )
    except RuntimeError as exc:
        print("Import status: failed")
        print("Database writes: none")
        print(f"Error: {exc}")
        return 2
    except Exception:
        print("Import status: failed")
        print("Database writes: none")
        print("Error: The Adzuna request could not be completed.")
        return 1

    session = None
    try:
        if args.commit:
            from database import SessionLocal

            session = SessionLocal()
            plan = import_catalogue(summary, session=session, commit=True)
        else:
            plan = import_catalogue(
                summary,
                session=None,
                commit=False,
                known_keys=state["keys"] if state["readable"] else None,
            )
    except Exception:
        print("Import status: failed")
        print("Database writes: none")
        print("Error: The Adzuna request could not be completed.")
        return 1
    finally:
        if session is not None:
            session.close()
    _print_catalogue(summary, plan, state, args.commit)
    if args.commit:
        return 0 if plan.status == "success" else 1
    return 0 if summary.requests_succeeded else 1


def _read_catalogue_state() -> dict:
    """Read stored identities. This rolls back and does not insert, update, or delete."""
    from sqlalchemy import text

    from database import engine

    needed = {
        "source",
        "external_job_id",
        "source_country",
        "source_url",
        "posted_at",
        "last_synced_at",
        "last_seen_at",
        "is_active",
        "is_matchable",
        "matchability_status",
        "matchability_reason",
        "description_is_snippet",
        "requirements_available",
    }
    empty = {
        "readable": False,
        "schema_ready": False,
        "jobs": None,
        "manual_jobs": None,
        "saved_jobs": None,
        "orphan_saved_jobs": None,
        "adzuna_jobs": None,
        "unique_index": False,
        "saved_foreign_key": False,
        "keys": set(),
    }
    try:
        with engine.connect() as connection:
            columns = {
                row[0]
                for row in connection.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_schema = 'public' AND table_name = 'jobs'"
                    )
                )
            }
            jobs = connection.execute(text("SELECT COUNT(*) FROM jobs")).scalar()
            saved = connection.execute(text("SELECT COUNT(*) FROM saved_jobs")).scalar()
            orphans = connection.execute(
                text(
                    "SELECT COUNT(*) FROM saved_jobs AS saved "
                    "WHERE NOT EXISTS (SELECT 1 FROM jobs WHERE jobs.id = saved.job_id)"
                )
            ).scalar()
            index_count = connection.execute(
                text("SELECT COUNT(*) FROM pg_indexes WHERE indexname = 'uq_jobs_source_listing'")
            ).scalar()
            foreign_keys = connection.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.table_constraints "
                    "WHERE table_schema = 'public' AND table_name = 'saved_jobs' "
                    "AND constraint_type = 'FOREIGN KEY'"
                )
            ).scalar()
            sync_table = connection.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'job_sync_logs'"
                )
            ).scalar()
            keys: set[tuple[str, str, str]] = set()
            manual = jobs
            if "source" in columns:
                manual = connection.execute(text("SELECT COUNT(*) FROM jobs WHERE source IS NULL")).scalar()
            if {"source", "source_country", "external_job_id"}.issubset(columns):
                rows = connection.execute(
                    text(
                        "SELECT source, source_country, external_job_id FROM jobs "
                        "WHERE source = 'adzuna' AND external_job_id IS NOT NULL"
                    )
                )
                keys = {(row[0], row[1], row[2]) for row in rows}
            connection.rollback()
    except Exception:
        return empty
    return {
        "readable": True,
        "schema_ready": needed.issubset(columns) and bool(index_count) and bool(sync_table),
        "jobs": jobs,
        "manual_jobs": manual,
        "saved_jobs": saved,
        "orphan_saved_jobs": orphans,
        "adzuna_jobs": len(keys),
        "unique_index": bool(index_count),
        "saved_foreign_key": bool(foreign_keys),
        "keys": keys,
    }


def _countries(args) -> list[str]:
    codes = args.countries or list(DEFAULT_DISCOVERY_COUNTRIES)
    cleaned = []
    for code in codes:
        value = str(code).strip().lower()
        if len(value) != 2 or not value.isalpha():
            raise RuntimeError("Each country must be a two-letter code.")
        if value not in cleaned:
            cleaned.append(value)
    return cleaned


def _searches(args) -> list[RoleSearch]:
    if args.use_catalog and args.queries:
        raise RuntimeError("Use either --use-catalog or --queries.")
    if not args.use_catalog and not args.queries:
        raise RuntimeError("Add --queries or --use-catalog.")
    if args.use_catalog:
        return list(ROLE_SEARCHES)
    known = {item.query.casefold(): item.category for item in ROLE_SEARCHES}
    return [RoleSearch(known.get(query.casefold(), "Custom"), query.strip()) for query in args.queries if query.strip()]


def _print_catalogue(summary: DiscoverySummary, plan: CatalogueSummary, state: dict, commit: bool) -> None:
    print(f"Import status: {plan.status}")
    print(f"Mode: {'commit' if commit else 'dry-run'}")
    if plan.wrote:
        print("Database writes: committed")
    elif plan.logs_written:
        print("Database writes: sync log only")
    else:
        print("Database writes: none")
    fetched_by_country: dict[str, int] = {}
    for attempt in summary.attempts:
        fetched_by_country[attempt.country] = fetched_by_country.get(attempt.country, 0) + attempt.fetched
    print(f"Requests attempted: {summary.requests_attempted}")
    print(f"Requests succeeded: {summary.requests_succeeded}")
    print(f"Requests failed: {summary.requests_failed}")
    print(f"Countries succeeded: {', '.join(summary.countries_succeeded) or 'none'}")
    print(f"Countries failed: {', '.join(summary.countries_failed) or 'none'}")
    print(f"Fetched: {summary.fetched}")
    print("Fetched by country: " + ", ".join(f"{_country_name(code)} {count}" for code, count in fetched_by_country.items()))
    print(f"Unique listings: {summary.unique}")
    print("Unique by country: " + ", ".join(f"{_country_name(code)} {count}" for code, count in summary.by_country.items()))
    print(f"Insertable listings: {plan.insertable}")
    print(f"Existing listings that would be updated: {plan.updated}")
    print(f"Duplicates skipped: {plan.duplicates_skipped}")
    print(f"Cross-query duplicates: {summary.cross_query_duplicates}")
    print(f"Same source id kept separate and not stored again: {plan.identity_conflicts}")
    print(f"Unmatchable listings: {plan.unmatchable}")
    print(f"Stored jobs: {_count(state.get('jobs'))}")
    print(f"Manually seeded jobs: {_count(state.get('manual_jobs'))}")
    print(f"Saved jobs: {_count(state.get('saved_jobs'))}")
    print(f"Saved jobs missing a listing: {_count(state.get('orphan_saved_jobs'))}")
    print(f"Stored Adzuna listings: {_count(state.get('adzuna_jobs'))}")
    print(f"Unique source index present: {'yes' if state.get('unique_index') else 'no'}")
    print(f"Saved-job foreign key present: {'yes' if state.get('saved_foreign_key') else 'no'}")
    for warning in _quality_warnings(summary, plan, state):
        print(f"Warning: {warning}")
    for attempt in summary.attempts:
        if attempt.status == "error":
            print(
                f"Failed search: {_country_name(attempt.country)} / {attempt.query} / "
                f"HTTP {attempt.status_code if attempt.status_code is not None else 'unavailable'} / "
                f"{attempt.error_message}"
            )
    if plan.error_message:
        print(f"Error: {plan.error_message}")
    shown = {code: 0 for code in summary.by_country}
    for job in summary.jobs:
        if shown.get(job.country, 0) >= 3:
            continue
        shown[job.country] = shown.get(job.country, 0) + 1
        _print_discovered(job)


def _quality_warnings(summary: DiscoverySummary, plan: CatalogueSummary, state: dict) -> list[str]:
    warnings = []
    if not state.get("readable"):
        warnings.append("Stored jobs could not be read. Insert and update counts assume no Adzuna listings are stored.")
    elif not state.get("schema_ready"):
        warnings.append("The job source migration has not been applied. Commit is not available until it has run.")
    if summary.requests_failed:
        warnings.append(
            f"{summary.requests_failed} provider searches failed. Listings already stored were not deactivated."
        )
    if summary.missing_required_skills:
        warnings.append(
            f"{summary.missing_required_skills} listings have no structured required skills and stay unmatchable."
        )
    if summary.incomplete_descriptions:
        warnings.append(f"{summary.incomplete_descriptions} descriptions are snippets or were not supplied.")
    if summary.missing_descriptions:
        warnings.append(f"{summary.missing_descriptions} listings have no description.")
    if summary.old_listings:
        warnings.append(f"{summary.old_listings} listings are older than 30 days.")
    if summary.undated_listings:
        warnings.append(f"{summary.undated_listings} listings have no posting date.")
    predicted = sum(job.salary_status == "predicted figure ignored" for job in summary.jobs)
    if predicted:
        warnings.append(f"{predicted} predicted salaries were ignored.")
    if plan.identity_conflicts:
        warnings.append(
            f"{plan.identity_conflicts} extra copies share a source id. Only the first copy can be stored."
        )
    if state.get("orphan_saved_jobs"):
        warnings.append(f"{state['orphan_saved_jobs']} saved jobs do not point at a listing.")
    return warnings


def _count(value) -> str:
    return "not read" if value is None else str(value)


def _print_discovered(job) -> None:
    posted = job.posted_at.isoformat() if job.posted_at is not None else "Not supplied"
    salary = "Not supplied"
    if job.salary_status == "supplied":
        salary = f"{job.salary_min if job.salary_min is not None else 'Not supplied'} to {job.salary_max if job.salary_max is not None else 'Not supplied'}"
        salary += f" {job.salary_currency}" if job.salary_currency else " (currency not supplied)"
    elif job.salary_status == "predicted figure ignored":
        salary = "Not supplied (Adzuna predicted a figure; it was not used)"
    print(f"- Title: {job.title}")
    print(f"  Company: {job.company}")
    print(f"  Location: {job.location}")
    print(f"  Country: {_country_name(job.country)} ({job.country})")
    print(f"  Source: {job.source}")
    print(f"  External ID: {job.external_job_id}")
    print(f"  Posted: {posted} ({job.posting_status})")
    print(f"  Link: {job.source_url or 'Not supplied'}")
    print(f"  Description: {job.description_status}, {len(job.description or '')} characters")
    print(f"  Salary: {salary}")
    print(f"  Employment type: {job.contract_type or 'Not supplied'}")
    print(f"  Hours: {job.contract_time or 'Not supplied'}")
    print(f"  Workplace: {job.workplace or 'Not supplied'}")
    print(f"  Categories: {', '.join(job.categories)}")
    print("  Required skills: not supplied by Adzuna")
    print("  Minimum experience: not supplied by Adzuna")


def _country_name(code: str) -> str:
    return COUNTRY_NAMES.get(code, code.upper())


def _print_summary(summary: ImportSummary, commit: bool) -> None:
    print(f"Import status: {summary.status}")
    print(f"Mode: {'commit' if commit else 'dry-run'}")
    print(f"Country: {summary.country}")
    print(f"Query: {summary.query}")
    print(f"Fetched: {summary.fetched}")
    print(f"Ready to import: {summary.ready}")
    print(f"Skipped: {summary.skipped}")
    print(f"Inserted: {summary.inserted}")
    print(f"Updated: {summary.updated}")
    print(f"Database writes: {'committed' if summary.wrote else 'none'}")
    if summary.error_message:
        print(f"Error: {summary.error_message}")
    for number, job in enumerate(summary.jobs, start=1):
        posted = job.posted_at.isoformat() if job.posted_at is not None else "Not supplied"
        description = job.description or ""
        preview = description[:180]
        print(f"{number}. Title: {job.title}")
        print(f"   Company: {job.company}")
        print(f"   Location: {job.location}")
        print(f"   Source: {job.source}")
        print(f"   Country: {job.source_country}")
        print(f"   External ID: {job.external_job_id}")
        print(f"   Posted: {posted}")
        print(f"   Link: {job.source_url or 'Not supplied'}")
        print(f"   Description characters: {len(description)}")
        if preview:
            print(f"   Description preview: {preview}")
        print("   Required skills: none supplied by Adzuna")
        print("   Minimum experience: not supplied by Adzuna")


if __name__ == "__main__":
    sys.exit(main())
