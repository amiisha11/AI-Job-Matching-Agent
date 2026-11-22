"""API address and cookie settings. No secrets are printed or stored."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

FRONTEND_DIR = Path(__file__).resolve().parent
if str(FRONTEND_DIR) not in sys.path:
    sys.path.insert(0, str(FRONTEND_DIR))

from app_config import LOCAL_API_URL, api_base_url, cookie_secure_enabled, streamlit_secret
from session_cookie import cookie_assignment, cookie_script

RENDER_URL = "https://ai-job-matching-api.onrender.com"


class _Secrets(dict):
    """A stand-in for st.secrets that does not read a secrets file."""

    def load_if_toml_exists(self) -> bool:
        return True


class _MissingSecrets:
    def load_if_toml_exists(self) -> bool:
        return False

    def __contains__(self, key: object) -> bool:
        raise AssertionError("a missing secrets file must not be read")


class _SecretError:
    def load_if_toml_exists(self) -> bool:
        return True

    def __contains__(self, key: object) -> bool:
        raise RuntimeError("postgresql://user:password@database.internal/app")

    def __getitem__(self, key: object):
        raise RuntimeError("GEMINI_API_KEY=hidden-value")


def test_environment_variable_sets_and_normalizes_the_api_url(monkeypatch):
    monkeypatch.setenv("API_URL", "  https://env.example.com///  ")
    monkeypatch.setattr("app_config.streamlit_secret", lambda name: "https://secret.example.com")
    assert api_base_url() == "https://env.example.com"


def test_streamlit_secret_is_used_when_the_environment_is_unset(monkeypatch):
    monkeypatch.delenv("API_URL", raising=False)
    monkeypatch.setattr("streamlit.secrets", _Secrets(API_URL=f"  {RENDER_URL}/  "))
    assert api_base_url() == RENDER_URL
    assert streamlit_secret("API_URL") == f"  {RENDER_URL}/  "


def test_environment_variable_wins_over_streamlit_secret(monkeypatch):
    monkeypatch.setenv("API_URL", "https://env.example.com/")
    monkeypatch.setattr("streamlit.secrets", _Secrets(API_URL=RENDER_URL, COOKIE_SECURE=True))
    assert api_base_url() == "https://env.example.com"


def test_missing_secrets_use_the_local_api(monkeypatch):
    monkeypatch.delenv("API_URL", raising=False)
    monkeypatch.setattr("streamlit.secrets", _MissingSecrets())
    assert streamlit_secret("API_URL") is None
    assert api_base_url() == LOCAL_API_URL


def test_blank_environment_falls_through_to_the_secret(monkeypatch):
    monkeypatch.setenv("API_URL", "   ")
    monkeypatch.setattr("streamlit.secrets", _Secrets(API_URL=RENDER_URL))
    assert api_base_url() == RENDER_URL


@pytest.mark.parametrize(
    ("value", "enabled"),
    [
        (True, True),
        (False, False),
        ("true", True),
        ("TRUE", True),
        ("yes", True),
        ("1", True),
        ("on", True),
        ("false", False),
        ("no", False),
        ("0", False),
        ("off", False),
    ],
)
def test_cookie_secure_accepts_booleans_and_strings(monkeypatch, value, enabled):
    monkeypatch.delenv("COOKIE_SECURE", raising=False)
    monkeypatch.setattr("streamlit.secrets", _Secrets(COOKIE_SECURE=value))
    assert cookie_secure_enabled() is enabled
    assignment = cookie_assignment("issued-token")
    assert "SameSite=Lax" in assignment
    assert ("; Secure" in assignment) is enabled


def test_cookie_environment_overrides_a_true_secret(monkeypatch):
    monkeypatch.setenv("COOKIE_SECURE", "false")
    monkeypatch.setattr("streamlit.secrets", _Secrets(COOKIE_SECURE=True))
    assert cookie_secure_enabled() is False
    assert "Secure" not in cookie_assignment("issued-token")
    assert "SameSite=Lax" in cookie_assignment("")


def test_secret_errors_do_not_reveal_values(monkeypatch):
    monkeypatch.delenv("API_URL", raising=False)
    monkeypatch.delenv("COOKIE_SECURE", raising=False)
    monkeypatch.setattr("streamlit.secrets", _SecretError())
    assert streamlit_secret("API_URL") is None
    assert streamlit_secret("COOKIE_SECURE") is None
    assert api_base_url() == LOCAL_API_URL
    script = cookie_script("issued-token")
    assert "password" not in script
    assert "GEMINI" not in script
    assert "database.internal" not in script
    assert "SameSite=Lax" in script
    assert "Secure" not in script


def test_configured_values_are_not_written_by_the_tests():
    """The examples above stay in memory. This file must not create a secrets file."""
    assert not (FRONTEND_DIR.parent / ".streamlit" / "secrets.toml").exists()
    with patch("app_config.streamlit_secret", return_value=None):
        assert "password" not in api_base_url()
