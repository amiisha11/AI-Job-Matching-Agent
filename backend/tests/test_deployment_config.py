"""Deployment settings. These tests do not call external services or write to the database."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import root
from settings import get_cors_origins

ROOT = Path(__file__).resolve().parents[2]


def test_health_endpoint_is_anonymous_and_has_no_secrets():
    body = root()
    assert body["status"] == "ok"
    assert "key" not in body["message"].casefold()
    assert "password" not in body["message"].casefold()


def test_cors_origins_come_from_the_environment(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    assert get_cors_origins() == ["http://localhost:8501", "http://127.0.0.1:8501"]
    monkeypatch.setenv("CORS_ORIGINS", "https://jobs.example.com, https://preview.example.com")
    assert get_cors_origins() == ["https://jobs.example.com", "https://preview.example.com"]


def test_deployment_files_pin_the_runtime_and_do_not_contain_secrets():
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    backend_requirements = (ROOT / "backend" / "requirements.txt").read_text(encoding="utf-8")
    render = (ROOT / "render.yaml").read_text(encoding="utf-8")
    runtime = (ROOT / "runtime.txt").read_text(encoding="utf-8").strip()
    assert requirements == backend_requirements
    for name in ("fastapi", "uvicorn", "streamlit", "sqlalchemy", "psycopg", "python-dotenv", "google-genai"):
        assert name in requirements
    assert runtime == "python-3.12.14"
    assert "--host 0.0.0.0" in render
    assert "--port $PORT" in render
    assert "healthCheckPath: /" in render
    assert "postgresql://" not in render
    assert "your_" not in render
    assert "sync: false" in render
