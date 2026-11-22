"""Add the guided-profile columns. This script does not run on its own.

Apply it only when you are ready to restart the API afterwards:

    .\\.venv\\Scripts\\python.exe backend\\migrate_candidate_profile.py

The statements add empty columns. They do not update or delete existing rows.
"""

import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent))

CANDIDATE_PROFILE_STATEMENTS = (
    "ALTER TABLE candidates ADD COLUMN IF NOT EXISTS degree TEXT",
    "ALTER TABLE candidates ADD COLUMN IF NOT EXISTS field_of_study TEXT",
    "ALTER TABLE candidates ADD COLUMN IF NOT EXISTS specialization TEXT",
    "ALTER TABLE candidates ADD COLUMN IF NOT EXISTS institution TEXT",
    "ALTER TABLE candidates ADD COLUMN IF NOT EXISTS graduation_year INTEGER",
    "ALTER TABLE candidates ADD COLUMN IF NOT EXISTS preferred_industries TEXT[] NOT NULL DEFAULT '{}'",
    "ALTER TABLE candidates ADD COLUMN IF NOT EXISTS preferred_countries TEXT[] NOT NULL DEFAULT '{}'",
    "ALTER TABLE candidates ADD COLUMN IF NOT EXISTS remote_preference VARCHAR(20)",
)


def main() -> int:
    from database import engine

    try:
        with engine.begin() as connection:
            for statement in CANDIDATE_PROFILE_STATEMENTS:
                connection.execute(text(statement))
    except Exception:
        print("Profile columns could not be added. No candidate rows were changed.")
        return 1
    print("Profile columns are ready. Existing candidate rows were kept.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
