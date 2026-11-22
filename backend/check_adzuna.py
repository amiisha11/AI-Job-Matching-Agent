"""Check the Adzuna search connection without storing any listings.

Run from the project root:

    .\\.venv\\Scripts\\python.exe backend\\check_adzuna.py
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.adzuna import AdzunaError, search_jobs


def main() -> int:
    """Fetch up to five GB listings for a fixed query and print safe fields only."""
    try:
        result = search_jobs(country="gb", page=1, what="Python Developer", results_per_page=5)
    except AdzunaError as exc:
        print("Connection status: failed")
        print(f"HTTP status code: {exc.status_code if exc.status_code is not None else 'unavailable'}")
        print("Jobs returned: 0")
        print(f"Error: {exc}")
        return 1
    except Exception:
        print("Connection status: failed")
        print("HTTP status code: unavailable")
        print("Jobs returned: 0")
        print("Error: The Adzuna request could not be completed.")
        return 1

    print("Connection status: connected")
    print(f"HTTP status code: {result.status_code}")
    print(f"Jobs returned: {len(result.jobs)}")
    if not result.jobs:
        print("No job listings were returned.")
        return 0
    for number, job in enumerate(result.jobs, start=1):
        print(f"{number}. Title: {job.title or 'Not supplied'}")
        print(f"   Company: {job.company or 'Not supplied'}")
        print(f"   Location: {job.location or 'Not supplied'}")
        print(f"   Posted: {job.created or 'Not supplied'}")
        print(f"   Link: {job.redirect_url or 'Not supplied'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
