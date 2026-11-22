"""Request dependencies for authentication.

Importing this module does not run a migration and does not issue a query.
"""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Candidate
from services.auth_repo import SqlAuthRepo
from services.auth_service import authenticate, owner_conflict


def get_auth_repo(db: Session = Depends(get_db)) -> SqlAuthRepo:
    """Build auth storage for this request."""
    return SqlAuthRepo(db)


def bearer_token(authorization: Annotated[str | None, Header()] = None) -> str:
    """Return the raw bearer token. The header is not logged."""
    if not authorization:
        return ""
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return ""
    return value.strip()


def get_current_candidate(
    raw_token: str = Depends(bearer_token),
    repo: SqlAuthRepo = Depends(get_auth_repo),
) -> Candidate:
    """Return the candidate for this session, or stop the request."""
    result = authenticate(repo, raw_token, datetime.now(timezone.utc))
    if not result.ok or result.candidate is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=result.message)
    candidate = repo.candidate_by_id(result.candidate["id"])
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Log in to continue.")
    return candidate


def ensure_owner(current: Candidate, requested_id: int) -> None:
    """Stop a request that targets a different candidate."""
    message = owner_conflict(current.id, requested_id)
    if message:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)
