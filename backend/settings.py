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


def _configured_secret(name: str, placeholder: str) -> str:
    """Read one secret. Callers must not print the returned value."""
    value = os.getenv(name, "").strip()
    if value == placeholder:
        return ""
    return value


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
