"""Add Adzuna source columns and the sync log table.

Existing job rows are kept. This command does not import listings.

Run from the project root:

    .\\.venv\\Scripts\\python.exe backend\\migrate_job_source.py
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import ensure_job_source_schema


def main() -> int:
    """Apply the additive job-source schema."""
    try:
        ensure_job_source_schema()
    except RuntimeError as exc:
        print(exc)
        return 1
    print("Job source columns are ready. No listings were imported.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
