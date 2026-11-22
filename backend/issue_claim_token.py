"""Issue one claim code for a passwordless profile.

Run this only for a person who already owns the profile. It prints the code
once and stores only its hash. It does not print database credentials.

    .\\.venv\\Scripts\\python.exe backend\\issue_claim_token.py --email name@example.com
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from database import SessionLocal
from services.auth_repo import SqlAuthRepo
from services.auth_service import issue_claim_token


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Issue a one-time profile claim code.")
    parser.add_argument("--email", required=True)
    args = parser.parse_args(argv)
    db = SessionLocal()
    try:
        result = issue_claim_token(SqlAuthRepo(db), args.email, datetime.now(timezone.utc))
    except Exception:
        print("The claim code could not be issued.")
        return 1
    finally:
        db.close()
    if not result.ok or not result.token:
        print(result.message)
        return 1
    print("Claim code issued. It expires in one hour and works once.")
    print(result.token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
