"""Authentication decisions with an in-memory store. No database connection."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.auth_service import (
    HASH_ITERATIONS,
    OTP_ATTEMPT_LIMIT,
    OTP_IP_LIMIT,
    OTP_SEND_LIMIT,
    OTP_SENT,
    EmailAlreadyUsed,
    authenticate,
    end_session,
    generate_otp,
    hash_otp,
    hash_password,
    hash_token,
    login_account,
    owner_conflict,
    public_candidate,
    register_account,
    send_setup_otp,
    setup_password,
    verify_password,
)

NOW = datetime(2026, 11, 21, tzinfo=timezone.utc)
FAST = 2_000
PEPPER = "test-pepper"


class MemoryRepo:
    """Stand-in for the database. It keeps hashes, not raw passwords."""

    def __init__(self):
        self.people = []
        self.sessions = []
        self.otps = []
        self.sends = []
        self.guards = {}
        self.next_id = 1
        self.next_otp_id = 1

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

    def record_otp_send(self, email, client_ip, created_at):
        self.sends.append(SimpleNamespace(email=email, client_ip=client_ip, created_at=created_at))

    def otp_sends_since(self, email, since):
        return [row for row in self.sends if row.email == email and row.created_at >= since]

    def otp_sends_for_ip_since(self, client_ip, since):
        return [row for row in self.sends if row.client_ip == client_ip and row.created_at >= since]

    def save_setup_otp(self, candidate_id, otp_hash, created_at, expires_at):
        row = SimpleNamespace(
            id=self.next_otp_id,
            candidate_id=candidate_id,
            otp_hash=otp_hash,
            created_at=created_at,
            expires_at=expires_at,
            used_at=None,
            failed_attempts=0,
        )
        self.next_otp_id += 1
        self.otps.append(row)
        return row

    def retire_unused_otps(self, candidate_id, used_at):
        for row in self.otps:
            if row.candidate_id == candidate_id and row.used_at is None:
                row.used_at = used_at

    def unused_otps(self, candidate_id):
        return [row for row in self.otps if row.candidate_id == candidate_id and row.used_at is None]

    def bump_otp_failures(self, candidate_id):
        for row in self.unused_otps(candidate_id):
            row.failed_attempts += 1

    def mark_otp_used(self, otp_row, used_at):
        otp_row.used_at = used_at

    def consume_setup_otp(self, otp_row, candidate, password_hash, used_at):
        if otp_row.used_at is not None:
            return False
        otp_row.used_at = used_at
        candidate.password_hash = password_hash
        return True

    def get_otp_guard(self, email):
        return self.guards.get(email)

    def save_otp_guard(self, email, failed_attempts, locked_until):
        self.guards[email] = SimpleNamespace(failed_attempts=failed_attempts, locked_until=locked_until)

    def clear_otp_guard(self, email):
        guard = self.guards.get(email)
        if guard is None:
            return
        guard.failed_attempts = 0
        guard.locked_until = None


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
    assert blocked.message == "This email already has a profile. Use Account setup to verify the email."

    needs_setup = login_account(repo, "ada@example.com", "correct-horse", NOW)
    assert needs_setup.status == 409
    assert needs_setup.message == "This profile has no password yet. Use Account setup to verify your email."
    assert existing.password_hash is None

    sent_to = []
    issued = _send(repo, "Ada@Example.com", NOW, sent_to)
    assert issued.status == 202
    assert issued.message == OTP_SENT
    assert issued.dev_otp is None
    assert len(sent_to) == 1
    assert sent_to[0][0] == "ada@example.com"
    assert len(sent_to[0][1]) == 6 and sent_to[0][1].isdigit()
    assert repo.otps[0].otp_hash == hash_otp(sent_to[0][1], PEPPER)
    assert sent_to[0][1] not in repo.otps[0].otp_hash

    ready = setup_password(repo, "Ada@Example.com", "correct-horse", sent_to[0][1], NOW, PEPPER, FAST)
    assert ready.ok
    assert ready.candidate["skills"] == ["Python", "SQL"]
    assert ready.candidate["years_experience"] == 3
    assert "password_hash" not in ready.candidate
    assert verify_password("correct-horse", existing.password_hash)
    assert repo.otps[0].used_at == NOW

    reused = setup_password(repo, "ada@example.com", "another-horse", sent_to[0][1], NOW, PEPPER, FAST)
    assert reused.status == 401
    assert reused.message == "The verification code is not valid."
    assert verify_password("correct-horse", existing.password_hash)
    assert not verify_password("another-horse", existing.password_hash)

    signed_in = login_account(repo, "ada@example.com", "correct-horse", NOW)
    assert signed_in.ok
    assert signed_in.candidate["id"] == 8
    kept_sessions = list(repo.sessions)
    again = setup_password(repo, "ada@example.com", "another-horse", sent_to[0][1], NOW, PEPPER, FAST)
    assert again.message == "The verification code is not valid."
    assert repo.sessions == kept_sessions
    assert authenticate(repo, signed_in.token, NOW).ok


def test_unknown_email_does_not_reveal_a_profile():
    repo = MemoryRepo()
    missing = login_account(repo, "missing@example.com", "correct-horse", NOW)
    assert missing.status == 401
    assert missing.message == "Incorrect email or password."
    sent_to = []
    waiting = _send(repo, "missing@example.com", NOW, sent_to)
    assert waiting.status == 202
    assert waiting.message == OTP_SENT
    assert waiting.dev_otp is None
    assert sent_to == []
    assert repo.otps == []
    rejected = setup_password(repo, "missing@example.com", "correct-horse", "123456", NOW, PEPPER, FAST)
    assert rejected.status == 401
    assert rejected.message == "The verification code is not valid."
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


def _sender(sent_to):
    def send(email, otp):
        sent_to.append((email, otp))

    return send


def _send(repo, email, now, sent_to, smtp_ready=True, dev_fallback=False, client_ip=None):
    return send_setup_otp(
        repo,
        email,
        now,
        PEPPER,
        smtp_ready,
        dev_fallback,
        _sender(sent_to),
        client_ip,
    )


def _passwordless(person_id=8):
    return SimpleNamespace(
        id=person_id,
        name="Ada Lovelace",
        email="ada@example.com",
        education=None,
        skills=["Python"],
        preferred_roles=[],
        preferred_locations=[],
        years_experience=1,
        password_hash=None,
    )


def test_setup_codes_expire_lock_and_do_not_replace_a_password():
    repo = MemoryRepo()
    existing = _passwordless()
    repo.people.append(existing)
    sent_to = []
    issued = _send(repo, "ada@example.com", NOW, sent_to)
    code = sent_to[0][1]
    expired = setup_password(repo, "ada@example.com", "correct-horse", code, NOW + timedelta(minutes=11), PEPPER, FAST)
    assert expired.status == 401
    assert existing.password_hash is None
    assert repo.otps[0].used_at is None

    for _ in range(OTP_ATTEMPT_LIMIT - 1):
        failed = setup_password(repo, "ada@example.com", "correct-horse", "000000", NOW, PEPPER, FAST)
        assert failed.status == 401
    locked = setup_password(repo, "ada@example.com", "correct-horse", code, NOW, PEPPER, FAST)
    assert locked.status == 429
    assert existing.password_hash is None
    assert repo.otps[0].used_at == NOW
    assert login_account(repo, "ada@example.com", "correct-horse", NOW).status == 409

    later = setup_password(repo, "ada@example.com", "correct-horse", code, NOW + timedelta(minutes=16), PEPPER, FAST)
    assert later.status == 401
    assert existing.password_hash is None


def test_a_new_code_replaces_the_previous_one_and_a_password_blocks_another():
    repo = MemoryRepo()
    existing = _passwordless()
    repo.people.append(existing)
    first_sent = []
    _send(repo, "ada@example.com", NOW, first_sent)
    second_sent = []
    second = _send(repo, "ada@example.com", NOW + timedelta(seconds=61), second_sent)
    assert second.status == 202
    old = setup_password(repo, "ada@example.com", "correct-horse", first_sent[0][1], NOW + timedelta(seconds=61), PEPPER, FAST)
    assert old.status == 401
    assert existing.password_hash is None
    ready = setup_password(repo, "ada@example.com", "correct-horse", second_sent[0][1], NOW + timedelta(seconds=61), PEPPER, FAST)
    assert ready.ok
    session = ready.token
    after = []
    blocked = _send(repo, "ada@example.com", NOW + timedelta(minutes=3), after)
    assert blocked.status == 202
    assert blocked.dev_otp is None
    assert after == []
    assert verify_password("correct-horse", existing.password_hash)
    assert authenticate(repo, session, NOW + timedelta(minutes=3)).ok


def test_send_limits_and_a_successful_check_clear_the_failure_guard():
    repo = MemoryRepo()
    existing = _passwordless()
    repo.people.append(existing)
    early = []
    assert _send(repo, "ada@example.com", NOW, early).status == 202
    cooled = _send(repo, "ada@example.com", NOW + timedelta(seconds=30), [])
    assert cooled.status == 429
    assert "Wait a minute" in cooled.message
    assert _send(repo, "ada@example.com", NOW + timedelta(seconds=61), []).status == 202
    assert _send(repo, "ada@example.com", NOW + timedelta(seconds=122), []).status == 202
    blocked = _send(repo, "ada@example.com", NOW + timedelta(seconds=183), [])
    assert blocked.status == 429
    assert len([row for row in repo.sends if row.email == "ada@example.com"]) == OTP_SEND_LIMIT

    other = MemoryRepo()
    for index in range(OTP_IP_LIMIT):
        other.people.append(
            SimpleNamespace(
                id=index + 1,
                name="Ada",
                email=f"ada{index}@example.com",
                education=None,
                skills=[],
                preferred_roles=[],
                preferred_locations=[],
                years_experience=0,
                password_hash=None,
            )
        )
        assert _send(other, f"ada{index}@example.com", NOW, [], client_ip="203.0.113.8").ok
    limited = _send(other, "extra@example.com", NOW + timedelta(seconds=1), [], client_ip="203.0.113.8")
    assert limited.status == 429

    guarded = MemoryRepo()
    person = _passwordless()
    guarded.people.append(person)
    sent = []
    _send(guarded, "ada@example.com", NOW, sent)
    for _ in range(4):
        assert setup_password(guarded, "ada@example.com", "correct-horse", "000000", NOW, PEPPER, FAST).status == 401
    done = setup_password(guarded, "ada@example.com", "correct-horse", sent[0][1], NOW, PEPPER, FAST)
    assert done.ok
    assert guarded.guards["ada@example.com"].failed_attempts == 0
    assert guarded.guards["ada@example.com"].locked_until is None


def test_development_fallback_is_explicit_and_a_failed_send_does_not_activate_the_code():
    repo = MemoryRepo()
    existing = _passwordless()
    repo.people.append(existing)
    missing = send_setup_otp(repo, "ada@example.com", NOW, "", False, True, lambda *_args: None)
    assert missing.status == 503
    assert missing.dev_otp is None

    hidden = _send(repo, "ada@example.com", NOW, [], smtp_ready=False, dev_fallback=False)
    assert hidden.status == 503
    assert hidden.dev_otp is None
    assert repo.otps == []

    shown = _send(repo, "ada@example.com", NOW, [], smtp_ready=False, dev_fallback=True)
    assert shown.dev_otp and len(shown.dev_otp) == 6
    assert repo.otps[0].otp_hash == hash_otp(shown.dev_otp, PEPPER)
    assert shown.dev_otp not in repo.otps[0].otp_hash

    def fail_send(_email, _otp):
        raise RuntimeError("mailbox password smtp.example")

    failed = send_setup_otp(repo, "ada@example.com", NOW + timedelta(seconds=61), PEPPER, True, False, fail_send)
    assert failed.status == 503
    assert failed.dev_otp is None
    assert "password" not in failed.message
    assert all(row.used_at is not None for row in repo.otps)
    assert existing.password_hash is None


def test_generated_codes_are_six_digits_and_old_claim_text_is_rejected():
    codes = {generate_otp() for _ in range(20)}
    assert all(len(code) == 6 and code.isdigit() for code in codes)
    repo = MemoryRepo()
    existing = _passwordless()
    repo.people.append(existing)
    rejected = setup_password(repo, "ada@example.com", "correct-horse", "not-a-claim-code", NOW, PEPPER, FAST)
    assert rejected.status == 422
    assert existing.password_hash is None
    assert repo.sessions == []
    sent = []
    _send(repo, "ada@example.com", NOW, sent)
    other = SimpleNamespace(
        id=9,
        name="Grace Hopper",
        email="grace@example.com",
        education=None,
        skills=[],
        preferred_roles=[],
        preferred_locations=[],
        years_experience=0,
        password_hash=None,
    )
    repo.people.append(other)
    wrong_account = setup_password(repo, "grace@example.com", "correct-horse", sent[0][1], NOW, PEPPER, FAST)
    assert wrong_account.status == 401
    assert other.password_hash is None
    assert existing.password_hash is None
    first = repo.consume_setup_otp(repo.otps[0], existing, "stored-hash", NOW)
    second = repo.consume_setup_otp(repo.otps[0], existing, "other-hash", NOW)
    assert first is True
    assert second is False
    assert existing.password_hash == "stored-hash"


def test_a_lost_insert_race_does_not_return_a_token():
    class Taken:
        def find_by_email(self, _email):
            return None

        def add_candidate(self, _name, _email, _password_hash):
            raise EmailAlreadyUsed

    result = register_account(Taken(), "Ada Lovelace", "ada@example.com", "correct-horse", NOW, FAST)
    assert result.status == 409
    assert result.token is None
