"""Frontend settings.

An environment variable wins. A Streamlit Community Cloud secret is next.
Local development keeps working when neither one is set.
"""

import os

LOCAL_API_URL = "http://127.0.0.1:8001"
_SECURE_TRUE = {"1", "true", "yes", "on"}


def streamlit_secret(name: str):
    """Return one Streamlit secret, or None when that secret is not configured.

    A missing secrets file is normal during local development. Errors are not
    reported, so a secrets file cannot leak its values into the page or the log.
    """
    try:
        import streamlit as st

        secrets = st.secrets
    except Exception:
        return None
    try:
        loader = getattr(secrets, "load_if_toml_exists", None)
        if callable(loader) and loader() is False:
            return None
        if name not in secrets:
            return None
        return secrets[name]
    except Exception:
        return None


def normalize_url(value: object) -> str:
    """Strip whitespace and trailing slashes from an API address."""
    return str(value).strip().rstrip("/")


def api_base_url() -> str:
    """Return the FastAPI address for this process."""
    raw = os.getenv("API_URL")
    if raw is not None and raw.strip():
        cleaned = normalize_url(raw)
        if cleaned:
            return cleaned
    secret = streamlit_secret("API_URL")
    if secret is not None and str(secret).strip():
        cleaned = normalize_url(secret)
        if cleaned:
            return cleaned
    return LOCAL_API_URL


def cookie_secure_enabled() -> bool:
    """True when the session cookie must be marked Secure."""
    raw = os.getenv("COOKIE_SECURE")
    if raw is not None and raw.strip() != "":
        return _is_true(raw)
    secret = streamlit_secret("COOKIE_SECURE")
    if secret is None:
        return False
    return _is_true(secret)


def _is_true(value: object) -> bool:
    """Accept a TOML boolean or the usual true/false strings."""
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in _SECURE_TRUE
