"""Login, registration, and session routes.

Request bodies are not logged. Responses contain a token and a profile,
never a password hash.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from deps import bearer_token, get_auth_repo, get_current_candidate
from models import Candidate
from services.auth_repo import SqlAuthRepo
from services.auth_service import (
    AuthResult,
    end_session,
    login_account,
    public_candidate,
    register_account,
    setup_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class Credentials(BaseModel):
    """Email and password. The password is checked and then discarded."""

    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=128)


class AccountBody(Credentials):
    """Name plus the login credentials."""

    name: str = Field(min_length=1, max_length=200)


class CandidatePublic(BaseModel):
    """Profile fields returned after login. There is no password field."""

    id: int
    name: str
    email: str
    education: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    specialization: str | None = None
    institution: str | None = None
    graduation_year: int | None = None
    skills: list[str] = Field(default_factory=list)
    preferred_roles: list[str] = Field(default_factory=list)
    preferred_industries: list[str] = Field(default_factory=list)
    preferred_locations: list[str] = Field(default_factory=list)
    preferred_countries: list[str] = Field(default_factory=list)
    remote_preference: str | None = None
    years_experience: int = 0


class AuthResponse(BaseModel):
    """A new session token and the profile it belongs to."""

    token: str
    candidate: CandidatePublic


def _finish(result: AuthResult) -> dict:
    if not result.ok or result.token is None or result.candidate is None:
        raise HTTPException(status_code=result.status, detail=result.message)
    return {"token": result.token, "candidate": result.candidate}


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(body: AccountBody, repo: SqlAuthRepo = Depends(get_auth_repo)) -> dict:
    """Create a profile with a password and return a session."""
    return _finish(register_account(repo, body.name, body.email, body.password, datetime.now(timezone.utc)))


@router.post("/login", response_model=AuthResponse)
def login(body: Credentials, repo: SqlAuthRepo = Depends(get_auth_repo)) -> dict:
    """Return a session for the matching email and password."""
    return _finish(login_account(repo, body.email, body.password, datetime.now(timezone.utc)))


@router.post("/setup-password", response_model=AuthResponse)
def setup(body: AccountBody, repo: SqlAuthRepo = Depends(get_auth_repo)) -> dict:
    """Set a password on a profile that does not have one yet."""
    return _finish(setup_password(repo, body.name, body.email, body.password, datetime.now(timezone.utc)))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(raw_token: str = Depends(bearer_token), repo: SqlAuthRepo = Depends(get_auth_repo)) -> Response:
    """Delete the current session."""
    end_session(repo, raw_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=CandidatePublic)
def me(current: Candidate = Depends(get_current_candidate)) -> dict:
    """Return the signed-in profile."""
    return public_candidate(current)
