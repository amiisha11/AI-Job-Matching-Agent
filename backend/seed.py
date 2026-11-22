"""Insert sample jobs from data/sample_jobs.csv.

A job is added only when that title and company are not already stored.
Existing jobs, candidates, and saved jobs are left unchanged.
"""

import csv
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
CSV_PATH = PROJECT_ROOT / "data" / "sample_jobs.csv"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import func, select

from database import SessionLocal
from models import Job


def parse_skills(value: str) -> list[str]:
    """Split a pipe-separated skill cell into a list."""
    skills: list[str] = []
    seen: set[str] = set()
    for part in value.split("|"):
        skill = part.strip()
        key = skill.casefold()
        if skill and key not in seen:
            seen.add(key)
            skills.append(skill)
    return skills


def clean_row(row: dict[str, str | None], line_number: int) -> Job | None:
    """Return a Job for a valid CSV row, or None when the row should be skipped."""
    title = (row.get("title") or "").strip()
    company = (row.get("company") or "").strip()
    location = (row.get("location") or "").strip()
    description = (row.get("description") or "").strip()
    raw_experience = (row.get("min_years_experience") or "").strip()

    if not title or not company or not location:
        print(f"Row {line_number}: missing title, company, or location. Skipped.")
        return None
    if len(title) > 200 or len(company) > 200 or len(location) > 200:
        print(f"Row {line_number}: title, company, or location is longer than 200 characters. Skipped.")
        return None
    if not raw_experience:
        print(f"Row {line_number}: min_years_experience is missing. Skipped.")
        return None
    try:
        min_experience = int(raw_experience)
    except ValueError:
        print(f"Row {line_number}: min_years_experience must be a whole number. Skipped.")
        return None
    if min_experience < 0:
        print(f"Row {line_number}: min_years_experience cannot be negative. Skipped.")
        return None

    return Job(
        title=title,
        company=company,
        location=location,
        description=description or None,
        required_skills=parse_skills(row.get("required_skills") or ""),
        min_experience=min_experience,
    )


def job_exists(db, title: str, company: str) -> bool:
    """True when this title and company are already stored, ignoring letter case."""
    existing = db.scalar(
        select(Job.id).where(
            func.lower(Job.title) == title.casefold(),
            func.lower(Job.company) == company.casefold(),
        )
    )
    return existing is not None


def seed_jobs() -> int:
    """Insert new sample jobs. Returns 0 on success and 1 when the file is missing."""
    if not CSV_PATH.is_file():
        print(f"CSV file not found: {CSV_PATH}")
        return 1

    inserted = 0
    skipped = 0
    invalid = 0
    seen: set[tuple[str, str]] = set()
    db = SessionLocal()
    try:
        with CSV_PATH.open(newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            if reader.fieldnames is None:
                print("The CSV file has no header row. No jobs were inserted.")
                return 1
            for line_number, row in enumerate(reader, start=2):
                job = clean_row(row, line_number)
                if job is None:
                    invalid += 1
                    continue
                key = (job.title.casefold(), job.company.casefold())
                if key in seen or job_exists(db, job.title, job.company):
                    skipped += 1
                    seen.add(key)
                    continue
                db.add(job)
                seen.add(key)
                inserted += 1
        db.commit()
    except Exception as exc:
        db.rollback()
        print(f"Seeding failed: {type(exc).__name__}. No rows were changed.")
        return 1
    finally:
        db.close()

    print(f"Inserted: {inserted}")
    print(f"Skipped: {skipped}")
    if invalid:
        print(f"Invalid rows: {invalid}")
    return 0


if __name__ == "__main__":
    sys.exit(seed_jobs())
