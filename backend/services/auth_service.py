"""Password hashing and login decisions.

Passwords are never stored or returned. Session tokens are random, and only
their SHA-256 hashes are kept. This module does not open the database.
"""

import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

HASH_ITERATIONS = 600_000
SESSION_HOURS = 12
SESSION_LIFETIME = timedelta(hours=SESSION_HOURS)
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_DUMMY_HASH: str | None = None


@dataclass
class AuthResult:
    """One authentication decision. The candidate dict never includes a password."""

    ok: bool
    status: int
    message: str = ""
    token: str | None = None
    candidate: dict | None = None


def hash_password(password: str, iterations: int = HASH_ITERATIONS) -> str:
    """Return a salted PBKDF2-HMAC-SHA256 hash. The same password hashes differently each time."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Compare a password with a stored hash without raising on a bad hash."""
    try:
        scheme, raw_iterations, salt_hex, digest_hex = stored.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        iterations = int(raw_iterations)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        if iterations < 1:
            return False
    except (AttributeError, TypeError, ValueError):
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(digest, expected)


def hash_token(raw_token: str) -> str:
    """Hash a session token before it is stored."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _dummy_hash() -> str:
    """A hash used when the account is missing, so the failure still does the same work."""
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = hash_password("not-a-real-password")
    return _DUMMY_HASH


def _fail(status: int, message: str) -> AuthResult:
    return AuthResult(ok=False, status=status, message=message)


def _ok(status: int, token: str, candidate) -> AuthResult:
    return AuthResult(ok=True, status=status, token=token, candidate=public_candidate(candidate))


def clean_name(value: str) -> str:
    """Trim a name the same way the profile form does."""
    return " ".join(str(value).split())


def public_candidate(candidate) -> dict:
    """Return profile fields that are safe to send to the browser."""
    return {
        "id": candidate.id,
        "name": candidate.name,
        "email": candidate.email,
        "education": candidate.education,
        "degree": getattr(candidate, "degree", None),
        "field_of_study": getattr(candidate, "field_of_study", None),
        "specialization": getattr(candidate, "specialization", None),
        "institution": getattr(candidate, "institution", None),
        "graduation_year": getattr(candidate, "graduation_year", None),
        "skills": list(candidate.skills or []),
        "preferred_roles": list(candidate.preferred_roles or []),
        "preferred_industries": list(getattr(candidate, "preferred_industries", None) or []),
        "preferred_locations": list(candidate.preferred_locations or []),
        "preferred_countries": list(getattr(candidate, "preferred_countries", None) or []),
        "remote_preference": getattr(candidate, "remote_preference", None),
        "years_experience": candidate.years_experience,
    }


def _name_error(name: str) -> str | None:
    if not name:
        return "Enter your name."
    if len(name) > 200:
        return "Name must be 200 characters or fewer."
    return None


def _email_error(email: str) -> str | None:
    if not _EMAIL_PATTERN.fullmatch(email):
        return "Enter an email address like name@example.com."
    if len(email) > 320:
        return "Email must be 320 characters or fewer."
    return None


def _password_error(password: str) -> str | None:
    if len(password) < 8:
        return "Use at least 8 characters."
    if len(password) > 128:
        return "Use at most 128 characters."
    return None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def register_account(repo, name: str, email: str, password: str, now: datetime, iterations: int = HASH_ITERATIONS) -> AuthResult:
    """Create a profile and a session, or explain why the email cannot be used."""
    cleaned_name = clean_name(name)
    cleaned_email = email.strip().lower()
    problem = _name_error(cleaned_name) or _email_error(cleaned_email) or _password_error(password)
    if problem:
        return _fail(422, problem)

    existing = repo.find_by_email(cleaned_email)
    if existing is not None and existing.password_hash:
        return _fail(409, "An account with this email already exists. Log in instead.")
    if existing is not None:
        return _fail(409, "This email already has a profile. Set a password on Account setup.")

    try:
        candidate = repo.add_candidate(cleaned_name, cleaned_email, hash_password(password, iterations))
    except EmailAlreadyUsed:
        return _fail(409, "An account with this email already exists. Log in instead.")
    token = repo.start_session(candidate.id, _as_utc(now), SESSION_LIFETIME)
    return _ok(201, token, candidate)


def login_account(repo, email: str, password: str, now: datetime) -> AuthResult:
    """Open a session for an existing password. Unknown emails and wrong passwords share one message."""
    cleaned_email = email.strip().lower()
    candidate = repo.find_by_email(cleaned_email) if _email_error(cleaned_email) is None else None
    if candidate is None or not candidate.password_hash:
        verify_password(password, _dummy_hash())
        if candidate is not None and not candidate.password_hash:
            return _fail(409, "This profile has no password yet. Use Account setup.")
        return _fail(401, "Incorrect email or password.")
    if not verify_password(password, candidate.password_hash):
        return _fail(401, "Incorrect email or password.")
    token = repo.start_session(candidate.id, _as_utc(now), SESSION_LIFETIME)
    return _ok(200, token, candidate)


def setup_password(repo, name: str, email: str, password: str, now: datetime, iterations: int = HASH_ITERATIONS) -> AuthResult:
    """Set the first password on a profile that does not have one.

    The email and the profile name must both match. This is not email-only
    access: a password is required afterwards, and a wrong name is rejected.
    """
    cleaned_name = clean_name(name)
    cleaned_email = email.strip().lower()
    problem = _name_error(cleaned_name) or _email_error(cleaned_email) or _password_error(password)
    if problem:
        return _fail(422, problem)

    candidate = repo.find_by_email(cleaned_email)
    if candidate is None:
        return _fail(404, "No profile is waiting for a password with that email.")
    if candidate.password_hash:
        return _fail(409, "This account already has a password. Log in.")
    if clean_name(candidate.name).casefold() != cleaned_name.casefold():
        return _fail(401, "The name does not match the profile for that email.")

    candidate.password_hash = hash_password(password, iterations)
    repo.set_password(candidate, candidate.password_hash)
    token = repo.start_session(candidate.id, _as_utc(now), SESSION_LIFETIME)
    return _ok(200, token, candidate)


def authenticate(repo, raw_token: str | None, now: datetime) -> AuthResult:
    """Return the candidate for a session token, or a login message."""
    if not raw_token:
        return _fail(401, "Log in to continue.")
    token_hash = hash_token(raw_token)
    session = repo.get_session(token_hash)
    if session is None:
        return _fail(401, "Log in to continue.")
    if _as_utc(session.expires_at) <= _as_utc(now):
        repo.delete_session(token_hash)
        return _fail(401, "Your session has expired. Log in again.")
    candidate = repo.candidate_by_id(session.candidate_id)
    if candidate is None:
        repo.delete_session(token_hash)
        return _fail(401, "Log in to continue.")
    return _ok(200, raw_token, candidate)


def end_session(repo, raw_token: str | None) -> None:
    """Remove a session. A missing token is already logged out."""
    if raw_token:
        repo.delete_session(hash_token(raw_token))


def owner_conflict(current_id: int, requested_id: int) -> str | None:
    """Block a signed-in user from opening another candidate's data."""
    if current_id != requested_id:
        return "You cannot open another candidate's profile."
    return None


class EmailAlreadyUsed(Exception):
    """The email was stored by someone else between the check and the insert."""
