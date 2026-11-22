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
OTP_LIFETIME = timedelta(minutes=10)
OTP_COOLDOWN = timedelta(seconds=60)
OTP_SEND_WINDOW = timedelta(minutes=15)
OTP_SEND_LIMIT = 3
OTP_IP_LIMIT = 10
OTP_ATTEMPT_LIMIT = 5
OTP_LOCK = timedelta(minutes=15)
OTP_SENT = (
    "If an eligible profile exists, a verification code has been sent to the registered email address."
)
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
    dev_otp: str | None = None


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


def generate_otp() -> str:
    """Return a six-digit code from the cryptographic random source."""
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(otp: str, pepper: str) -> str:
    """Return the HMAC-SHA256 of a setup code. The raw code is not recoverable from it."""
    return hmac.new(pepper.encode("utf-8"), str(otp).encode("utf-8"), hashlib.sha256).hexdigest()


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
        return _fail(409, "This email already has a profile. Use Account setup to verify the email.")

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
            return _fail(409, "This profile has no password yet. Use Account setup to verify your email.")
        return _fail(401, "Incorrect email or password.")
    if not verify_password(password, candidate.password_hash):
        return _fail(401, "Incorrect email or password.")
    token = repo.start_session(candidate.id, _as_utc(now), SESSION_LIFETIME)
    return _ok(200, token, candidate)


def send_setup_otp(
    repo,
    email: str,
    now: datetime,
    pepper: str,
    smtp_ready: bool,
    dev_fallback: bool,
    send_email,
    client_ip: str | None = None,
) -> AuthResult:
    """Request a setup code for a passwordless profile.

    Unknown emails and accounts that already have a password get the same
    response and do not receive a code. The raw code is returned only when the
    explicit local development fallback is on and mail is not configured.
    """
    cleaned_email = email.strip().lower()
    problem = _email_error(cleaned_email)
    if problem:
        return _fail(422, problem)
    if not pepper:
        return _fail(503, "Email verification is not configured.")
    if not smtp_ready and not dev_fallback:
        return _fail(503, "Email delivery is not configured.")

    moment = _as_utc(now)
    limited = _otp_send_limit(repo, cleaned_email, client_ip, moment)
    if limited is not None:
        return limited
    repo.record_otp_send(cleaned_email, _clean_ip(client_ip), moment)

    candidate = repo.find_by_email(cleaned_email)
    if candidate is None or candidate.password_hash:
        return AuthResult(ok=True, status=202, message=OTP_SENT)

    repo.retire_unused_otps(candidate.id, moment)
    raw_otp = generate_otp()
    repo.save_setup_otp(candidate.id, hash_otp(raw_otp, pepper), moment, moment + OTP_LIFETIME)
    if dev_fallback and not smtp_ready:
        return AuthResult(ok=True, status=202, message=OTP_SENT, dev_otp=raw_otp)
    try:
        send_email(cleaned_email, raw_otp)
    except Exception:
        repo.retire_unused_otps(candidate.id, moment)
        return _fail(503, "Email delivery is temporarily unavailable.")
    return AuthResult(ok=True, status=202, message=OTP_SENT)


def setup_password(
    repo,
    email: str,
    password: str,
    otp: str,
    now: datetime,
    pepper: str,
    iterations: int = HASH_ITERATIONS,
) -> AuthResult:
    """Set the first password when the emailed code matches its stored HMAC.

    The profile name is not accepted as proof. A wrong, expired, or reused code
    does not change the password or existing sessions.
    """
    cleaned_email = email.strip().lower()
    problem = _email_error(cleaned_email) or _password_error(password)
    if problem:
        return _fail(422, problem)
    code = str(otp or "").strip()
    if not re.fullmatch(r"\d{6}", code):
        return _fail(422, "Enter the six-digit verification code.")
    if not pepper:
        return _fail(503, "Email verification is not configured.")

    moment = _as_utc(now)
    guard = repo.get_otp_guard(cleaned_email)
    locked_until = _as_utc(guard.locked_until) if guard is not None and guard.locked_until else None
    if locked_until is not None and locked_until > moment:
        _dummy_otp_check(pepper)
        return _fail(429, "Too many attempts. Try again in 15 minutes.")

    candidate = repo.find_by_email(cleaned_email)
    matched = _matching_otp(repo, candidate, code, pepper, moment) if candidate is not None else None
    if matched is None:
        _dummy_otp_check(pepper)
        _record_otp_failure(repo, cleaned_email, candidate, guard, moment)
        return _fail(401, "The verification code is not valid.")
    if candidate.password_hash:
        repo.mark_otp_used(matched, moment)
        return _fail(409, "This account already has a password. Log in.")

    password_hash = hash_password(password, iterations)
    if not repo.consume_setup_otp(matched, candidate, password_hash, moment):
        _record_otp_failure(repo, cleaned_email, candidate, guard, moment)
        return _fail(401, "The verification code is not valid.")
    repo.clear_otp_guard(cleaned_email)
    token = repo.start_session(candidate.id, moment, SESSION_LIFETIME)
    return _ok(200, token, candidate)


def _clean_ip(client_ip: str | None) -> str | None:
    if not client_ip:
        return None
    text = str(client_ip).strip()
    return text[:64] or None


def _otp_send_limit(repo, email: str, client_ip: str | None, now: datetime) -> AuthResult | None:
    recent = repo.otp_sends_since(email, now - OTP_SEND_WINDOW)
    if recent:
        latest = max(_as_utc(row.created_at) for row in recent)
        if now - latest < OTP_COOLDOWN:
            return _fail(429, "Resend temporarily unavailable. Wait a minute and try again.")
    if len(recent) >= OTP_SEND_LIMIT:
        return _fail(429, "Too many verification codes were requested. Try again later.")
    ip_address = _clean_ip(client_ip)
    if ip_address is not None:
        ip_rows = repo.otp_sends_for_ip_since(ip_address, now - OTP_SEND_WINDOW)
        if len(ip_rows) >= OTP_IP_LIMIT:
            return _fail(429, "Too many verification codes were requested. Try again later.")
    return None


def _dummy_otp_check(pepper: str) -> None:
    """Do the same HMAC comparison when the code does not match a stored row."""
    hmac.compare_digest(hash_otp("000000", pepper), hash_otp("000001", pepper))


def _matching_otp(repo, candidate, code: str, pepper: str, now: datetime):
    wanted = hash_otp(code, pepper)
    found = None
    for row in repo.unused_otps(candidate.id):
        if hmac.compare_digest(row.otp_hash, wanted):
            found = row
    if found is None or _as_utc(found.expires_at) <= now:
        return None
    return found


def _record_otp_failure(repo, email: str, candidate, guard, now: datetime) -> None:
    attempts = 0 if guard is None else int(guard.failed_attempts or 0)
    attempts += 1
    locked_until = None
    if candidate is not None:
        repo.bump_otp_failures(candidate.id)
    if attempts >= OTP_ATTEMPT_LIMIT:
        locked_until = now + OTP_LOCK
        attempts = 0
        if candidate is not None:
            repo.retire_unused_otps(candidate.id, now)
    repo.save_otp_guard(email, attempts, locked_until)


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
