"""Database storage for passwords and sessions.

Only password hashes and token hashes are written. The raw token and the
password never go into the database.
"""

import secrets
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import AuthSession, Candidate, ClaimGuard, ClaimToken, EmailSetupOTP, OtpGuard, OtpSend
from services.auth_service import EmailAlreadyUsed, hash_token


class SqlAuthRepo:
    """Auth storage for one request session."""

    def __init__(self, db: Session):
        self.db = db

    def find_by_email(self, email: str) -> Candidate | None:
        return self.db.scalar(select(Candidate).where(Candidate.email == email))

    def add_candidate(self, name: str, email: str, password_hash: str) -> Candidate:
        candidate = Candidate(
            name=name,
            email=email,
            education=None,
            skills=[],
            preferred_roles=[],
            preferred_locations=[],
            years_experience=0,
            password_hash=password_hash,
        )
        self.db.add(candidate)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise EmailAlreadyUsed from None
        self.db.refresh(candidate)
        return candidate

    def set_password(self, candidate: Candidate, password_hash: str) -> None:
        candidate.password_hash = password_hash
        self.db.commit()
        self.db.refresh(candidate)

    def start_session(self, candidate_id: int, now: datetime, lifetime: timedelta) -> str:
        raw_token = secrets.token_urlsafe(32)
        self.db.add(
            AuthSession(
                candidate_id=candidate_id,
                token_hash=hash_token(raw_token),
                expires_at=now + lifetime,
            )
        )
        self.db.commit()
        return raw_token

    def get_session(self, token_hash: str) -> AuthSession | None:
        return self.db.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash))

    def delete_session(self, token_hash: str) -> None:
        row = self.get_session(token_hash)
        if row is None:
            return
        self.db.delete(row)
        self.db.commit()

    def candidate_by_id(self, candidate_id: int) -> Candidate | None:
        return self.db.get(Candidate, candidate_id)

    def save_claim_token(self, candidate_id: int, token_hash: str, expires_at: datetime, created_at: datetime) -> None:
        self.db.add(
            ClaimToken(
                candidate_id=candidate_id,
                token_hash=token_hash,
                expires_at=expires_at,
                created_at=created_at,
            )
        )
        self.db.commit()

    def retire_unused_claims(self, candidate_id: int, used_at: datetime) -> None:
        rows = self.db.scalars(
            select(ClaimToken).where(ClaimToken.candidate_id == candidate_id, ClaimToken.used_at.is_(None))
        )
        for row in rows:
            row.used_at = used_at
        self.db.commit()

    def unused_claims(self, candidate_id: int) -> list[ClaimToken]:
        return list(
            self.db.scalars(
                select(ClaimToken).where(ClaimToken.candidate_id == candidate_id, ClaimToken.used_at.is_(None))
            )
        )

    def mark_claim_used(self, claim: ClaimToken, used_at: datetime) -> None:
        claim.used_at = used_at
        self.db.commit()

    def get_claim_guard(self, email: str) -> ClaimGuard | None:
        return self.db.scalar(select(ClaimGuard).where(ClaimGuard.email == email))

    def save_claim_guard(self, email: str, failed_attempts: int, locked_until: datetime | None) -> None:
        guard = self.get_claim_guard(email)
        if guard is None:
            guard = ClaimGuard(email=email, failed_attempts=failed_attempts, locked_until=locked_until)
            self.db.add(guard)
        else:
            guard.failed_attempts = failed_attempts
            guard.locked_until = locked_until
        self.db.commit()

    def clear_claim_guard(self, email: str) -> None:
        guard = self.get_claim_guard(email)
        if guard is None:
            return
        guard.failed_attempts = 0
        guard.locked_until = None
        self.db.commit()

    def record_otp_send(self, email: str, client_ip: str | None, created_at: datetime) -> None:
        self.db.add(OtpSend(email=email, client_ip=client_ip, created_at=created_at))
        self.db.commit()

    def otp_sends_since(self, email: str, since: datetime) -> list[OtpSend]:
        return list(
            self.db.scalars(select(OtpSend).where(OtpSend.email == email, OtpSend.created_at >= since))
        )

    def otp_sends_for_ip_since(self, client_ip: str, since: datetime) -> list[OtpSend]:
        return list(
            self.db.scalars(
                select(OtpSend).where(OtpSend.client_ip == client_ip, OtpSend.created_at >= since)
            )
        )

    def save_setup_otp(self, candidate_id: int, otp_hash: str, created_at: datetime, expires_at: datetime) -> EmailSetupOTP:
        row = EmailSetupOTP(
            candidate_id=candidate_id,
            otp_hash=otp_hash,
            created_at=created_at,
            expires_at=expires_at,
            failed_attempts=0,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def retire_unused_otps(self, candidate_id: int, used_at: datetime) -> None:
        rows = self.db.scalars(
            select(EmailSetupOTP).where(
                EmailSetupOTP.candidate_id == candidate_id,
                EmailSetupOTP.used_at.is_(None),
            )
        )
        for row in rows:
            row.used_at = used_at
        self.db.commit()

    def unused_otps(self, candidate_id: int) -> list[EmailSetupOTP]:
        return list(
            self.db.scalars(
                select(EmailSetupOTP).where(
                    EmailSetupOTP.candidate_id == candidate_id,
                    EmailSetupOTP.used_at.is_(None),
                )
            )
        )

    def bump_otp_failures(self, candidate_id: int) -> None:
        for row in self.unused_otps(candidate_id):
            row.failed_attempts = int(row.failed_attempts or 0) + 1
        self.db.commit()

    def mark_otp_used(self, otp_row: EmailSetupOTP, used_at: datetime) -> None:
        otp_row.used_at = used_at
        self.db.commit()

    def consume_setup_otp(self, otp_row: EmailSetupOTP, candidate: Candidate, password_hash: str, used_at: datetime) -> bool:
        """Mark one unused code used and set the password in the same transaction."""
        result = self.db.execute(
            update(EmailSetupOTP)
            .where(EmailSetupOTP.id == otp_row.id, EmailSetupOTP.used_at.is_(None))
            .values(used_at=used_at)
        )
        if result.rowcount != 1:
            self.db.rollback()
            return False
        candidate.password_hash = password_hash
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            return False
        self.db.refresh(candidate)
        return True

    def get_otp_guard(self, email: str) -> OtpGuard | None:
        return self.db.scalar(select(OtpGuard).where(OtpGuard.email == email))

    def save_otp_guard(self, email: str, failed_attempts: int, locked_until: datetime | None) -> None:
        guard = self.get_otp_guard(email)
        if guard is None:
            guard = OtpGuard(email=email, failed_attempts=failed_attempts, locked_until=locked_until)
            self.db.add(guard)
        else:
            guard.failed_attempts = failed_attempts
            guard.locked_until = locked_until
        self.db.commit()

    def clear_otp_guard(self, email: str) -> None:
        guard = self.get_otp_guard(email)
        if guard is None:
            return
        guard.failed_attempts = 0
        guard.locked_until = None
        self.db.commit()
