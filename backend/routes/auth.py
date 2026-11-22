"""Login, registration, and session routes.

Request bodies are not logged. Responses contain a token and a profile,
never a password hash.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
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
    change_password,
    confirm_reset,
    send_reset_otp,
    send_setup_otp,
    setup_password,
)
from services.email_delivery import deliver_reset_code, deliver_setup_code
from settings import dev_otp_fallback_allowed, get_email_otp_pepper, smtp_is_configured

router = APIRouter(prefix="/auth", tags=["auth"])


class Credentials(BaseModel):
    """Email and password. The password is checked and then discarded."""

    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=128)


class AccountBody(Credentials):
    """Name plus the login credentials."""

    name: str = Field(min_length=1, max_length=200)


class SendOtpBody(BaseModel):
    """The email that should receive a setup code."""

    email: str = Field(min_length=1, max_length=320)


class ChangePasswordBody(BaseModel):
    """The signed-in user's current password and the replacement."""

    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=1, max_length=128)


class ResetConfirmBody(BaseModel):
    """A reset code and the replacement password. The profile name is not proof."""

    email: str = Field(min_length=1, max_length=320)
    otp: str = Field(min_length=1, max_length=12)
    new_password: str = Field(min_length=1, max_length=128)


class SetupBody(BaseModel):
    """A six-digit code plus the password to set. The profile name is not proof."""

    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=128)
    otp: str = Field(min_length=1, max_length=12)


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


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded.strip():
        return forwarded.split(",")[0].strip()[:64] or None
    if request.client is None:
        return None
    return request.client.host[:64]


@router.post("/setup/send-otp")
def send_otp(body: SendOtpBody, request: Request, repo: SqlAuthRepo = Depends(get_auth_repo)) -> JSONResponse:
    """Ask for a setup code. The response does not say whether the email exists."""
    result = send_setup_otp(
        repo,
        body.email,
        datetime.now(timezone.utc),
        pepper=get_email_otp_pepper(),
        smtp_ready=smtp_is_configured(),
        dev_fallback=dev_otp_fallback_allowed(),
        send_email=deliver_setup_code,
        client_ip=_client_ip(request),
    )
    if not result.ok:
        raise HTTPException(status_code=result.status, detail=result.message)
    payload = {"detail": result.message}
    if result.dev_otp:
        payload["dev_otp"] = result.dev_otp
    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=payload)


@router.post("/setup-password", response_model=AuthResponse)
def setup(body: SetupBody, repo: SqlAuthRepo = Depends(get_auth_repo)) -> dict:
    """Set a password when the emailed code matches the stored HMAC."""
    return _finish(
        setup_password(
            repo,
            body.email,
            body.password,
            body.otp,
            datetime.now(timezone.utc),
            get_email_otp_pepper(),
        )
    )


def _accepted(result: AuthResult) -> JSONResponse:
    if not result.ok:
        raise HTTPException(status_code=result.status, detail=result.message)
    payload = {"detail": result.message}
    if result.dev_otp:
        payload["dev_otp"] = result.dev_otp
    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=payload)


@router.post("/password-reset/send-otp")
def send_reset(body: SendOtpBody, request: Request, repo: SqlAuthRepo = Depends(get_auth_repo)) -> JSONResponse:
    """Ask for a reset code. The response does not say whether the email exists."""
    return _accepted(
        send_reset_otp(
            repo,
            body.email,
            datetime.now(timezone.utc),
            pepper=get_email_otp_pepper(),
            smtp_ready=smtp_is_configured(),
            dev_fallback=dev_otp_fallback_allowed(),
            send_email=deliver_reset_code,
            client_ip=_client_ip(request),
        )
    )


@router.post("/password-reset/confirm")
def reset_password(body: ResetConfirmBody, repo: SqlAuthRepo = Depends(get_auth_repo)) -> dict:
    """Set a new password from a reset code. The caller must log in again."""
    result = confirm_reset(
        repo,
        body.email,
        body.otp,
        body.new_password,
        datetime.now(timezone.utc),
        get_email_otp_pepper(),
    )
    if not result.ok:
        raise HTTPException(status_code=result.status, detail=result.message)
    return {"detail": result.message}


@router.post("/change-password")
def change(
    body: ChangePasswordBody,
    raw_token: str = Depends(bearer_token),
    current: Candidate = Depends(get_current_candidate),
    repo: SqlAuthRepo = Depends(get_auth_repo),
) -> dict:
    """Replace the signed-in user's password. Other sessions for that user are signed out."""
    result = change_password(repo, current, body.current_password, body.new_password, raw_token)
    if not result.ok:
        raise HTTPException(status_code=result.status, detail=result.message)
    return {"detail": result.message}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(raw_token: str = Depends(bearer_token), repo: SqlAuthRepo = Depends(get_auth_repo)) -> Response:
    """Delete the current session."""
    end_session(repo, raw_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=CandidatePublic)
def me(current: Candidate = Depends(get_current_candidate)) -> dict:
    """Return the signed-in profile."""
    return public_candidate(current)
