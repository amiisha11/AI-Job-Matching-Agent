"""Load configuration from the project root .env file.

DATABASE_URL stays in .env. This module reads it and never writes it back.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"
DEFAULT_GEMINI_EMBEDDING_MODEL = "models/gemini-embedding-2"
DEFAULT_SKILL_SIMILARITY_THRESHOLD = 0.75
_PLACEHOLDER_GEMINI_KEY = "your_gemini_api_key_here"
_PLACEHOLDER_ADZUNA_APP_ID = "your_adzuna_app_id_here"
_PLACEHOLDER_ADZUNA_APP_KEY = "your_adzuna_app_key_here"


def get_database_url() -> str:
    """Return the PostgreSQL URL from the environment."""
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is missing. Set it in the .env file at the project root."
        )
    return database_url


def get_gemini_api_key() -> str:
    """Return the Gemini key, or an empty string when it is not set."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if api_key == _PLACEHOLDER_GEMINI_KEY:
        return ""
    return api_key


def get_gemini_model() -> str:
    """Return GEMINI_MODEL, or gemini-3.8-flash when it is blank."""
    model = os.getenv("GEMINI_MODEL", "").strip()
    return model or DEFAULT_GEMINI_MODEL


def get_gemini_embedding_model() -> str:
    """Return GEMINI_EMBEDDING_MODEL, or models/gemini-embedding-2 when it is blank."""
    model = os.getenv("GEMINI_EMBEDDING_MODEL", "").strip()
    return model or DEFAULT_GEMINI_EMBEDDING_MODEL


def get_adzuna_app_id() -> str:
    """Return the Adzuna application id, or an empty string when it is not set."""
    return _configured_secret("ADZUNA_APP_ID", _PLACEHOLDER_ADZUNA_APP_ID)


def get_adzuna_app_key() -> str:
    """Return the Adzuna application key, or an empty string when it is not set."""
    return _configured_secret("ADZUNA_APP_KEY", _PLACEHOLDER_ADZUNA_APP_KEY)


def get_jooble_api_key(country: str) -> str:
    """Return the Jooble key for one country. Callers must not print it."""
    code = str(country or "").strip().casefold()
    if code == "in":
        return _configured_secret("JOOBLE_IN_API_KEY", "your_jooble_in_api_key_here")
    if code in {"gb", "uk"}:
        return _configured_secret("JOOBLE_UK_API_KEY", "your_jooble_uk_api_key_here")
    return ""


def _configured_secret(name: str, placeholder: str) -> str:
    """Read one secret. Callers must not print the returned value."""
    value = os.getenv(name, "").strip()
    if value == placeholder:
        return ""
    return value


def get_cors_origins() -> list[str]:
    """Return the browser origins allowed to call the API."""
    raw_value = os.getenv("CORS_ORIGINS", "").strip()
    if not raw_value:
        return ["http://localhost:8501", "http://127.0.0.1:8501"]
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def get_app_env() -> str:
    """Return the deployment environment. An empty value means production."""
    value = os.getenv("APP_ENV", "").strip().lower()
    return value or "production"


def dev_otp_fallback_allowed() -> bool:
    """Return whether a local screen may show a setup code instead of emailing it.

    Production never allows this, even when EMAIL_OTP_DEV_MODE is set.
    """
    if get_app_env() != "development":
        return False
    return _flag("EMAIL_OTP_DEV_MODE", False)


def get_email_otp_pepper() -> str:
    """Return the HMAC pepper for setup codes. Callers must not print it."""
    return _configured_secret("EMAIL_OTP_PEPPER", "your_email_otp_pepper_here")


def get_email_provider() -> str:
    """Return smtp or google_apps_script. An empty value keeps the local SMTP path."""
    value = os.getenv("EMAIL_PROVIDER", "").strip().lower()
    if value in {"", "smtp"}:
        return "smtp"
    if value == "google_apps_script":
        return "google_apps_script"
    return ""


def get_google_apps_script_settings() -> dict:
    """Return the Apps Script web app URL and shared secret. Callers must not print the secret."""
    url = os.getenv("GOOGLE_APPS_SCRIPT_URL", "").strip()
    if url and not url.lower().startswith("https://"):
        url = ""
    return {
        "url": url,
        "secret": _configured_secret("GOOGLE_APPS_SCRIPT_SECRET", "your_google_apps_script_secret_here"),
    }


def email_is_configured() -> bool:
    """True when the selected provider has the settings it needs. There is no SMTP fallback."""
    provider = get_email_provider()
    if provider == "google_apps_script":
        settings = get_google_apps_script_settings()
        return bool(settings["url"] and settings["secret"])
    if provider == "smtp":
        return smtp_is_configured()
    return False


def get_smtp_settings() -> dict:
    """Return SMTP settings. The password is included only for the mail client."""
    port_text = os.getenv("SMTP_PORT", "").strip()
    try:
        port = int(port_text) if port_text else 587
    except ValueError:
        port = 587
    use_ssl = _flag("SMTP_USE_SSL", False)
    return {
        "host": os.getenv("SMTP_HOST", "").strip(),
        "port": port,
        "username": os.getenv("SMTP_USERNAME", "").strip(),
        "password": os.getenv("SMTP_PASSWORD", "").strip(),
        "from_email": os.getenv("SMTP_FROM_EMAIL", "").strip(),
        "use_ssl": use_ssl,
        "use_tls": _flag("SMTP_USE_TLS", not use_ssl),
    }


def smtp_is_configured() -> bool:
    """True when a host and From address are both set."""
    settings = get_smtp_settings()
    return bool(settings["host"] and settings["from_email"])


def _flag(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def get_skill_similarity_threshold() -> float:
    """Return the minimum cosine similarity that counts as a related skill."""
    raw_value = os.getenv("GEMINI_SKILL_SIMILARITY_THRESHOLD", "").strip()
    if not raw_value:
        return DEFAULT_SKILL_SIMILARITY_THRESHOLD
    try:
        threshold = float(raw_value)
    except ValueError:
        return DEFAULT_SKILL_SIMILARITY_THRESHOLD
    if not 0 <= threshold <= 1:
        return DEFAULT_SKILL_SIMILARITY_THRESHOLD
    return threshold
