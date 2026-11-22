"""SMTP delivery and production OTP settings. No network connection and no secrets are printed."""

import logging
import smtplib
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.exceptions import RequestValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import hide_rejected_values
from services.email_delivery import TIMEOUT_SECONDS, EmailDeliveryError, deliver_setup_code
from settings import dev_otp_fallback_allowed, get_app_env, get_email_otp_pepper, get_smtp_settings, smtp_is_configured

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


def test_smtp_port_defaults_to_starttls(monkeypatch):
    monkeypatch.delenv("SMTP_PORT", raising=False)
    monkeypatch.delenv("SMTP_USE_TLS", raising=False)
    monkeypatch.delenv("SMTP_USE_SSL", raising=False)
    settings = get_smtp_settings()
    assert settings["port"] == 587
    assert settings["use_tls"] is True
    assert settings["use_ssl"] is False
