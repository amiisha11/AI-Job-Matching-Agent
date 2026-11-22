"""Create the password-reset code table.

Existing candidates, passwords, sessions, saved jobs, preparation rows,
account-setup codes, and claim-token history are left in place. Nothing is dropped.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from database import ensure_auth_schema


def main() -> int:
    ensure_auth_schema()
    print("Password reset tables are ready. Existing accounts were kept.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
