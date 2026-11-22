"""Authentication decisions with an in-memory store. No database connection."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.auth_service import (
    CLAIM_ATTEMPT_LIMIT,
    HASH_ITERATIONS,
    EmailAlreadyUsed,
    authenticate,
    end_session,
    hash_password,
    hash_token,
    issue_claim_token,
    login_account,
    owner_conflict,
    public_candidate,
    register_account,
    setup_password,
    verify_password,
)

NOW = datetime(2026, 11, 21, tzinfo=timezone.utc)
FAST = 2_000


class MemoryRepo:
    """Stand-in for the database. It keeps hashes, not raw passwords."""

    def __init__(self):
        self.people = []
        self.sessions = []
        self.claims = []
        self.guards = {}
        self.next_id = 1

    def find_by_email(self, email):
        return next((person for person in self.people if person.email == email), None)

    def add_candidate(self, name, email, password_hash):
        person = SimpleNamespace(
            id=self.next_id,
            name=name,
            email=email,
            education=None,
            skills=[],
            preferred_roles=[],
            preferred_locations=[],
            years_experience=0,
            password_hash=password_hash,
        )
        self.next_id += 1
        self.people.append(person)
        return person

    def set_password(self, candidate, password_hash):
        candidate.password_hash = password_hash

    def start_session(self, candidate_id, now, lifetime):
        raw = f"session-{candidate_id}-{len(self.sessions) + 1}"
        self.sessions.append(
            SimpleNamespace(
                token_hash=hash_token(raw),
                candidate_id=candidate_id,
                expires_at=now + lifetime,
            )
        )
        return raw

    def get_session(self, token_hash):
        return next((row for row in self.sessions if row.token_hash == token_hash), None)

    def delete_session(self, token_hash):
        self.sessions = [row for row in self.sessions if row.token_hash != token_hash]

    def candidate_by_id(self, candidate_id):
        return next((person for person in self.people if person.id == candidate_id), None)

    def save_claim_token(self, candidate_id, token_hash, expires_at, created_at):
        self.claims.append(
            SimpleNamespace(
                candidate_id=candidate_id,
                token_hash=token_hash,
                expires_at=expires_at,
                used_at=None,
                created_at=created_at,
            )
        )

    def retire_unused_claims(self, candidate_id, used_at):
        for claim in self.claims:
            if claim.candidate_id == candidate_id and claim.used_at is None:
                claim.used_at = used_at

    def unused_claims(self, candidate_id):
        return [claim for claim in self.claims if claim.candidate_id == candidate_id and claim.used_at is None]

    def mark_claim_used(self, claim, used_at):
        claim.used_at = used_at

    def get_claim_guard(self, email):
        return self.guards.get(email)

    def save_claim_guard(self, email, failed_attempts, locked_until):
        self.guards[email] = SimpleNamespace(failed_attempts=failed_attempts, locked_until=locked_until)

    def clear_claim_guard(self, email):
        self.guards.pop(email, None)


def test_password_hash_is_salted_and_checkable():
    first = hash_password("correct-horse", iterations=FAST)
    second = hash_password("correct-horse", iterations=FAST)
    assert first.startswith(f"pbkdf2_sha256${FAST}$")
    assert first != second
    assert first != "correct-horse"
    assert verify_password("correct-horse", first)
    assert not verify_password("other-horse", first)


def test_production_hash_uses_the_full_iteration_count():
    stored = hash_password("correct-horse")
    assert stored.startswith(f"pbkdf2_sha256${HASH_ITERATIONS}$")
    assert verify_password("correct-horse", stored)


def test_register_creates_a_profile_and_hides_the_password():
    repo = MemoryRepo()
    result = register_account(repo, " Ada Lovelace ", "Ada@Example.com", "correct-horse", NOW, FAST)
    assert result.ok
    assert result.candidate["id"] == 1
    assert result.candidate["email"] == "ada@example.com"
    assert result.candidate["name"] == "Ada Lovelace"
    assert result.candidate["skills"] == []
    assert "password" not in result.candidate
    assert "password_hash" not in result.candidate
    stored = repo.people[0].password_hash
    assert stored != "correct-horse"
    assert verify_password("correct-horse", stored)
    session = repo.sessions[0]
    assert session.token_hash == hash_token(result.token)
    assert session.token_hash != result.token


def test_duplicate_email_and_bad_password_do_not_create_a_second_profile():
    repo = MemoryRepo()
    register_account(repo, "Ada Lovelace", "ada@example.com", "correct-horse", NOW, FAST)
    duplicate = register_account(repo, "Ada Lovelace", "ada@example.com", "correct-horse", NOW, FAST)
    assert duplicate.status == 409
    assert duplicate.message == "An account with this email already exists. Log in instead."
    assert len(repo.people) == 1

    short = register_account(repo, "Grace Hopper", "grace@example.com", "short", NOW, FAST)
    assert short.status == 422
    assert short.message == "Use at least 8 characters."
    assert len(repo.people) == 1

    wrong = login_account(repo, "ada@example.com", "wrong-horse", NOW)
    assert wrong.status == 401
    assert wrong.message == "Incorrect email or password."
    assert wrong.token is None


def test_existing_profile_needs_the_stored_name_before_a_password_is_set():
    repo = MemoryRepo()
    existing = SimpleNamespace(
        id=8,
        name="Ada Lovelace",
        email="ada@example.com",
        education=None,
        skills=["Python", "SQL"],
        preferred_roles=["Analyst"],
        preferred_locations=["London"],
        years_experience=3,
        password_hash=None,
    )
    repo.people.append(existing)
    blocked = register_account(repo, "Ada Lovelace", "ada@example.com", "correct-horse", NOW, FAST)
    assert blocked.status == 409
    assert blocked.message == "This email already has a profile. Ask an administrator for a claim code."

    needs_setup = login_account(repo, "ada@example.com", "correct-horse", NOW)
    assert needs_setup.status == 409
    assert needs_setup.message == "This profile has no password yet. Account setup requires a claim code."
    assert existing.password_hash is None

    by_name = setup_password(repo, "ada@example.com", "correct-horse", "", NOW, FAST)
    assert by_name.status == 422
    assert by_name.message == "A claim code is required."
    assert existing.password_hash is None
    assert repo.sessions == []

    issued = issue_claim_token(repo, "Ada@Example.com", NOW)
    assert issued.ok
    assert issued.token
    assert issued.token not in {claim.token_hash for claim in repo.claims}
    assert repo.claims[0].token_hash == hash_token(issued.token)

    ready = setup_password(repo, "Ada@Example.com", "correct-horse", issued.token, NOW, FAST)
    assert ready.ok
    assert ready.candidate["skills"] == ["Python", "SQL"]
    assert ready.candidate["years_experience"] == 3
    assert "password_hash" not in ready.candidate
    assert verify_password("correct-horse", existing.password_hash)
    assert repo.claims[0].used_at == NOW

    reused = setup_password(repo, "ada@example.com", "another-horse", issued.token, NOW, FAST)
    assert reused.status == 401
    assert reused.message == "The claim code is not valid."
    assert verify_password("correct-horse", existing.password_hash)
    assert not verify_password("another-horse", existing.password_hash)

    signed_in = login_account(repo, "ada@example.com", "correct-horse", NOW)
    assert signed_in.ok
    assert signed_in.candidate["id"] == 8
    kept_sessions = list(repo.sessions)
    again = setup_password(repo, "ada@example.com", "another-horse", issued.token, NOW, FAST)
    assert again.message == "The claim code is not valid."
    assert repo.sessions == kept_sessions
    assert authenticate(repo, signed_in.token, NOW).ok


def test_unknown_email_does_not_reveal_a_profile():
    repo = MemoryRepo()
    missing = login_account(repo, "missing@example.com", "correct-horse", NOW)
    assert missing.status == 401
    assert missing.message == "Incorrect email or password."
    waiting = setup_password(repo, "missing@example.com", "correct-horse", "not-a-real-code", NOW, FAST)
    assert waiting.status == 401
    assert waiting.message == "The claim code is not valid."
    assert repo.people == []


def test_expired_and_logged_out_sessions_are_rejected():
    repo = MemoryRepo()
    created = register_account(repo, "Ada Lovelace", "ada@example.com", "correct-horse", NOW, FAST)
    current = authenticate(repo, created.token, NOW + timedelta(hours=1))
    assert current.ok
    assert public_candidate(repo.people[0])["email"] == "ada@example.com"

    expired = authenticate(repo, created.token, NOW + timedelta(hours=13))
    assert expired.status == 401
    assert expired.message == "Your session has expired. Log in again."
    assert repo.get_session(hash_token(created.token)) is None

    fresh = login_account(repo, "ada@example.com", "correct-horse", NOW)
    end_session(repo, fresh.token)
    signed_out = authenticate(repo, fresh.token, NOW)
    assert signed_out.message == "Log in to continue."
    assert owner_conflict(fresh.candidate["id"], 99) == "You cannot open another candidate's profile."
    assert owner_conflict(fresh.candidate["id"], fresh.candidate["id"]) is None


def test_a_valid_claim_does_not_replace_an_existing_password_or_session():
    repo = MemoryRepo()
    existing = SimpleNamespace(
        id=8,
        name="Ada Lovelace",
        email="ada@example.com",
        education=None,
        skills=["Python"],
        preferred_roles=[],
        preferred_locations=[],
        years_experience=1,
        password_hash=hash_password("correct-horse", FAST),
    )
    repo.people.append(existing)
    raw = "already-issued-code"
    repo.save_claim_token(existing.id, hash_token(raw), NOW + timedelta(hours=1), NOW)
    session = repo.start_session(existing.id, NOW, timedelta(hours=12))

    result = setup_password(repo, "ada@example.com", "another-horse", raw, NOW, FAST)

    assert result.status == 409
    assert result.message == "This account already has a password. Log in."
    assert verify_password("correct-horse", existing.password_hash)
    assert not verify_password("another-horse", existing.password_hash)
    assert repo.claims[0].used_at == NOW
    assert authenticate(repo, session, NOW).ok


def test_claim_codes_expire_lock_and_do_not_replace_a_password():
    repo = MemoryRepo()
    existing = SimpleNamespace(
        id=8,
        name="Ada Lovelace",
        email="ada@example.com",
        education=None,
        skills=["Python"],
        preferred_roles=[],
        preferred_locations=[],
        years_experience=1,
        password_hash=None,
    )
    repo.people.append(existing)
    issued = issue_claim_token(repo, "ada@example.com", NOW)
    expired = setup_password(repo, "ada@example.com", "correct-horse", issued.token, NOW + timedelta(hours=2), FAST)
    assert expired.status == 401
    assert existing.password_hash is None
    assert repo.claims[0].used_at is None

    for _ in range(CLAIM_ATTEMPT_LIMIT - 1):
        failed = setup_password(repo, "ada@example.com", "correct-horse", "wrong-code", NOW, FAST)
        assert failed.status == 401
    locked = setup_password(repo, "ada@example.com", "correct-horse", issued.token, NOW, FAST)
    assert locked.status == 429
    assert existing.password_hash is None

    ready = setup_password(repo, "ada@example.com", "correct-horse", issued.token, NOW + timedelta(minutes=16), FAST)
    assert ready.ok
    first_session = ready.token
    assert authenticate(repo, first_session, NOW + timedelta(minutes=16)).ok

    replacement = issue_claim_token(repo, "ada@example.com", NOW)
    assert replacement.status == 409
    assert replacement.token is None
    assert verify_password("correct-horse", existing.password_hash)
    assert authenticate(repo, first_session, NOW + timedelta(minutes=16)).ok


def test_a_lost_insert_race_does_not_return_a_token():
    class Taken:
        def find_by_email(self, _email):
            return None

        def add_candidate(self, _name, _email, _password_hash):
            raise EmailAlreadyUsed

    result = register_account(Taken(), "Ada Lovelace", "ada@example.com", "correct-horse", NOW, FAST)
    assert result.status == 409
    assert result.token is None
