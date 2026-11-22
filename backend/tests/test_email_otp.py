"""SMTP delivery and production OTP settings. No network connection and no secrets are printed."""

import io
import json
import logging
import smtplib
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import requests
from fastapi.exceptions import RequestValidationError
from urllib3.response import HTTPResponse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import hide_rejected_values
from services.auth_service import hash_otp, send_reset_otp, send_setup_otp
from services.email_delivery import (
    TIMEOUT_SECONDS,
    EmailDeliveryError,
    deliver_reset_code,
    deliver_setup_code,
)
from settings import (
    dev_otp_fallback_allowed,
    email_is_configured,
    get_app_env,
    get_email_otp_pepper,
    get_smtp_settings,
    smtp_is_configured,
)

CODE = "654321"
MAILBOX_SECRET = "mailbox-secret"


class FakeSMTP:
    def __init__(self, host, port, timeout=None, context=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.context = context
        self.started = False
        self.message = None
        self.login_args = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def ehlo(self):
        return None

    def starttls(self, context=None):
        self.started = True
        self.context = context

    def login(self, username, password):
        self.login_args = (username, password)

    def send_message(self, message):
        self.message = message


def _smtp_env(monkeypatch, **extra):
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USERNAME", "mailer")
    monkeypatch.setenv("SMTP_PASSWORD", MAILBOX_SECRET)
    monkeypatch.setenv("SMTP_FROM_EMAIL", "jobs@example.com")
    monkeypatch.setenv("SMTP_USE_TLS", "true")
    monkeypatch.setenv("SMTP_USE_SSL", "false")
    for name, value in extra.items():
        monkeypatch.setenv(name, value)


def test_defaults_keep_production_from_showing_a_code(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("EMAIL_OTP_DEV_MODE", raising=False)
    monkeypatch.setenv("EMAIL_OTP_PEPPER", "your_email_otp_pepper_here")
    assert get_app_env() == "production"
    assert dev_otp_fallback_allowed() is False
    assert get_email_otp_pepper() == ""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("EMAIL_OTP_DEV_MODE", "true")
    assert dev_otp_fallback_allowed() is False
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("EMAIL_OTP_DEV_MODE", "false")
    assert dev_otp_fallback_allowed() is False
    monkeypatch.setenv("EMAIL_OTP_DEV_MODE", "true")
    assert dev_otp_fallback_allowed() is True


def test_smtp_message_uses_starttls_and_keeps_the_code_out_of_the_subject(monkeypatch):
    _smtp_env(monkeypatch)
    clients = []

    def build(*args, **kwargs):
        client = FakeSMTP(*args, **kwargs)
        clients.append(client)
        return client

    with patch("smtplib.SMTP", build):
        deliver_setup_code("ada@example.com", CODE)
    client = clients[0]
    assert client.timeout == TIMEOUT_SECONDS
    assert client.started is True
    assert client.login_args == ("mailer", MAILBOX_SECRET)
    subject = client.message["Subject"]
    assert CODE not in subject
    assert "AI Job Matching Agent" in subject
    assert CODE in client.message.get_body(preferencelist=("plain",)).get_content()
    assert "10 minutes" in client.message.get_body(preferencelist=("plain",)).get_content()
    assert "ignore this email" in client.message.get_body(preferencelist=("html",)).get_content()


def test_missing_smtp_settings_do_not_open_a_connection(monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_FROM_EMAIL", raising=False)
    assert smtp_is_configured() is False
    with patch("smtplib.SMTP", side_effect=AssertionError("connection")):
        with pytest.raises(EmailDeliveryError):
            deliver_setup_code("ada@example.com", CODE)


def test_smtp_timeout_and_authentication_failure_are_sanitized(monkeypatch, caplog):
    _smtp_env(monkeypatch)
    caplog.set_level(logging.WARNING)
    with patch("smtplib.SMTP", side_effect=TimeoutError("timed out talking to secret-host")):
        with pytest.raises(EmailDeliveryError):
            deliver_setup_code("ada@example.com", CODE)
    with patch("smtplib.SMTP", side_effect=smtplib.SMTPAuthenticationError(535, b"bad mailbox-secret")):
        with pytest.raises(EmailDeliveryError):
            deliver_setup_code("ada@example.com", CODE)
    logged = caplog.text
    assert CODE not in logged
    assert MAILBOX_SECRET not in logged
    assert "secret-host" not in logged
    assert "TimeoutError" in logged
    assert "SMTPAuthenticationError" in logged


def test_validation_errors_do_not_echo_an_otp_or_password():
    import asyncio

    exc = RequestValidationError(
        [
            {"loc": ("body", "otp"), "msg": CODE, "type": "value_error"},
            {"loc": ("body", "password"), "msg": "correct-horse", "type": "value_error"},
        ]
    )
    response = asyncio.run(hide_rejected_values(None, exc))
    body = response.body.decode()
    assert CODE not in body
    assert "correct-horse" not in body


SCRIPT_URL = "https://script.google.com/macros/s/deployment/exec"
SHARED_SECRET = "shared-secret"
FINAL_URL = "https://script.googleusercontent.com/macros/echo?user_content_key=abc"


class FakeResponse:
    def __init__(self, status, body, url=FINAL_URL):
        self.status_code = status
        self._body = body
        self.url = url
        self.history = []

    def json(self):
        if isinstance(self._body, str):
            return json.loads(self._body)
        return self._body


class FakeSession:
    def __init__(self, response=None, error=None):
        self.response = response if response is not None else FakeResponse(200, {"ok": True})
        self.error = error
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def post(self, url, data=None, headers=None, timeout=None, allow_redirects=None):
        self.calls.append(
            {
                "url": url,
                "data": data,
                "headers": headers,
                "timeout": timeout,
                "allow_redirects": allow_redirects,
            }
        )
        if self.error is not None:
            raise self.error
        return self.response


def _script_env(monkeypatch, **extra):
    monkeypatch.setenv("EMAIL_PROVIDER", "google_apps_script")
    monkeypatch.setenv("GOOGLE_APPS_SCRIPT_URL", SCRIPT_URL)
    monkeypatch.setenv("GOOGLE_APPS_SCRIPT_SECRET", SHARED_SECRET)
    for name, value in extra.items():
        monkeypatch.setenv(name, value)


def _patch_session(session):
    return patch("services.email_delivery.requests.Session", return_value=session)


def test_apps_script_posts_the_code_and_accepts_ok_true(monkeypatch):
    _script_env(monkeypatch)
    session = FakeSession()
    with _patch_session(session):
        deliver_setup_code("ada@example.com", CODE)
    call = session.calls[0]
    payload = json.loads(call["data"])
    assert set(payload) == {"secret", "to", "otp"}
    assert payload == {"secret": SHARED_SECRET, "to": "ada@example.com", "otp": CODE}
    assert call["headers"]["Content-Type"] == "application/json"
    assert call["url"] == SCRIPT_URL
    assert call["allow_redirects"] is True
    assert call["timeout"] == (10, 20)


def test_apps_script_requires_url_and_secret_and_https(monkeypatch):
    _script_env(monkeypatch)
    monkeypatch.setenv("GOOGLE_APPS_SCRIPT_URL", "")
    session = FakeSession()
    with _patch_session(session):
        with pytest.raises(EmailDeliveryError, match="not-configured"):
            deliver_setup_code("ada@example.com", CODE)
    monkeypatch.setenv("GOOGLE_APPS_SCRIPT_URL", SCRIPT_URL)
    monkeypatch.setenv("GOOGLE_APPS_SCRIPT_SECRET", "")
    with _patch_session(session):
        with pytest.raises(EmailDeliveryError, match="not-configured"):
            deliver_reset_code("ada@example.com", CODE)
    monkeypatch.setenv("GOOGLE_APPS_SCRIPT_SECRET", "your_google_apps_script_secret_here")
    with _patch_session(session):
        with pytest.raises(EmailDeliveryError, match="not-configured"):
            deliver_setup_code("ada@example.com", CODE)
    monkeypatch.setenv("GOOGLE_APPS_SCRIPT_SECRET", SHARED_SECRET)
    monkeypatch.setenv("GOOGLE_APPS_SCRIPT_URL", "http://script.google.com/macros/s/deployment/exec")
    with _patch_session(session):
        with pytest.raises(EmailDeliveryError, match="not-configured"):
            deliver_setup_code("ada@example.com", CODE)
    assert session.calls == []


def test_apps_script_timeout_network_http_and_json_failures_are_sanitized(monkeypatch, caplog):
    _script_env(monkeypatch)
    caplog.set_level(logging.WARNING)
    cases = [
        (FakeSession(error=requests.Timeout("timed out at " + SHARED_SECRET)), "timeout"),
        (FakeSession(error=requests.ConnectionError("dns " + CODE + " ada@example.com")), "network"),
        (FakeSession(error=requests.TooManyRedirects("redirect loop")), "redirect"),
        (FakeSession(FakeResponse(502, "down")), "http-error"),
        (FakeSession(FakeResponse(200, "not-json")), "invalid-json"),
        (FakeSession(FakeResponse(200, {"ok": False})), "rejected"),
        (FakeSession(FakeResponse(403, {"ok": False, "error": "bad secret " + SHARED_SECRET})), "unauthorized"),
        (
            FakeSession(FakeResponse(200, {"ok": False, "error": "Service invoked too many times for one day: email"})),
            "quota",
        ),
    ]
    for session, category in cases:
        with _patch_session(session):
            with pytest.raises(EmailDeliveryError, match="delivery-failed"):
                deliver_setup_code("ada@example.com", CODE)
        assert category in caplog.text
    logged = caplog.text
    assert SHARED_SECRET not in logged
    assert CODE not in logged
    assert "ada@example.com" not in logged
    assert "too many times" not in logged


def test_apps_script_follows_the_content_service_redirect(monkeypatch):
    _script_env(monkeypatch)
    seen = []

    class Adapter(requests.adapters.HTTPAdapter):
        def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None, **_kwargs):
            seen.append((request.method, request.url, request.body))
            if "script.googleusercontent.com" in request.url:
                status = 200
                payload = b'{"ok": true}'
                headers = {"Content-Type": "application/json"}
            else:
                status = 302
                payload = b""
                headers = {"Location": FINAL_URL}
            raw = HTTPResponse(
                body=io.BytesIO(payload),
                status=status,
                headers=headers,
                preload_content=False,
            )
            return self.build_response(request, raw)

    original_session = requests.Session

    def session_factory():
        session = original_session()
        session.mount("https://", Adapter())
        return session

    with patch("services.email_delivery.requests.Session", session_factory):
        deliver_reset_code("ada@example.com", CODE)
    assert seen[0][0] == "POST"
    assert seen[0][1] == SCRIPT_URL
    posted = json.loads(seen[0][2])
    assert posted["to"] == "ada@example.com"
    assert posted["otp"] == CODE
    assert seen[1][0] == "GET"
    assert seen[1][1] == FINAL_URL


def test_apps_script_failure_does_not_fall_back_to_smtp(monkeypatch):
    _script_env(monkeypatch)
    _smtp_env(monkeypatch)
    monkeypatch.setenv("EMAIL_PROVIDER", "google_apps_script")
    session = FakeSession(error=requests.ConnectionError("down"))
    with _patch_session(session), patch("smtplib.SMTP", side_effect=AssertionError("smtp fallback")):
        with pytest.raises(EmailDeliveryError, match="delivery-failed"):
            deliver_setup_code("ada@example.com", CODE)
    assert email_is_configured() is True
    monkeypatch.setenv("GOOGLE_APPS_SCRIPT_SECRET", "")
    assert smtp_is_configured() is True
    assert email_is_configured() is False


def test_setup_and_reset_codes_are_delivered_by_apps_script(monkeypatch):
    _script_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("EMAIL_OTP_DEV_MODE", "true")
    moment = datetime(2026, 11, 22, tzinfo=timezone.utc)
    passwordless = SimpleNamespace(id=4, email="ada@example.com", password_hash=None)
    passworded = SimpleNamespace(id=8, email="ada@example.com", password_hash="stored-hash")

    setup_repo = _MailRepo(passwordless)
    setup_session = FakeSession()
    with _patch_session(setup_session):
        setup = send_setup_otp(
            setup_repo,
            "Ada@Example.com",
            moment,
            "pepper",
            smtp_ready=True,
            dev_fallback=False,
            send_email=deliver_setup_code,
        )
    setup_payload = json.loads(setup_session.calls[0]["data"])
    assert setup.status == 202
    assert setup.dev_otp is None
    assert setup_payload["to"] == "ada@example.com"
    assert hash_otp(setup_payload["otp"], "pepper") == setup_repo.hashes[0]

    reset_repo = _MailRepo(passworded)
    reset_session = FakeSession()
    with _patch_session(reset_session):
        reset = send_reset_otp(
            reset_repo,
            "Ada@Example.com",
            moment,
            "pepper",
            smtp_ready=True,
            dev_fallback=False,
            send_email=deliver_reset_code,
        )
    reset_payload = json.loads(reset_session.calls[0]["data"])
    assert reset.status == 202
    assert reset.dev_otp is None
    assert reset_payload["to"] == "ada@example.com"
    assert hash_otp(reset_payload["otp"], "pepper") == reset_repo.hashes[0]


class _MailRepo:
    def __init__(self, person):
        self.person = person
        self.hashes = []

    def otp_sends_since(self, _email, _since):
        return []

    def otp_sends_for_ip_since(self, _ip, _since):
        return []

    def record_otp_send(self, _email, _ip, _moment):
        return None

    def find_by_email(self, email):
        if self.person is not None and self.person.email == email:
            return self.person
        return None

    def retire_unused_otps(self, _candidate_id, _used_at):
        return None

    def save_setup_otp(self, _candidate_id, otp_hash, _created_at, _expires_at):
        self.hashes.append(otp_hash)

    def retire_unused_resets(self, _candidate_id, _used_at):
        return None

    def save_reset_otp(self, _candidate_id, otp_hash, _created_at, _expires_at):
        self.hashes.append(otp_hash)


def test_smtp_port_defaults_to_starttls(monkeypatch):
    monkeypatch.delenv("SMTP_PORT", raising=False)
    monkeypatch.delenv("SMTP_USE_TLS", raising=False)
    monkeypatch.delenv("SMTP_USE_SSL", raising=False)
    settings = get_smtp_settings()
    assert settings["port"] == 587
    assert settings["use_tls"] is True
    assert settings["use_ssl"] is False
