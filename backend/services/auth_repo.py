"""Database storage for passwords and sessions.

Only password hashes and token hashes are written. The raw token and the
password never go into the database.
"""

import secrets
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import AuthSession, Candidate
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
