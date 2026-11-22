"""Add category columns and the provider category table.

Existing job rows, saved jobs, and matchability flags stay as they are.
This command does not import listings.

Run from the project root only when a category import has been reviewed:

    .\\.venv\\Scripts\\python.exe backend\\migrate_job_categories.py
"""

import sys
from pathlib import Path

from sqlalchemy import text

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import engine
from services.job_schema import JOB_CATEGORY_STATEMENTS


def main() -> int:
    """Apply the additive category schema. Listings are not imported."""
    try:
        with engine.begin() as connection:
            for statement in JOB_CATEGORY_STATEMENTS:
                connection.execute(text(statement))
    except Exception:
        print("Category columns could not be prepared. No listings were imported.")
        return 1
    print("Category columns are ready. No listings were imported.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
