"""Calls the FastAPI backend. This module does not open the database."""

import requests

from app_config import api_base_url


def split_csv(value: str) -> list[str]:
    """Turn a comma-separated box into the lists the API expects."""
    return [item.strip() for item in value.split(",") if item.strip()]


def error_text(response: requests.Response) -> str:
    """Turn a FastAPI error into a sentence for the page."""
    try:
        detail = response.json().get("detail", "")
    except ValueError:
        detail = ""

    if isinstance(detail, str) and detail:
        return detail
    if isinstance(detail, list):
        parts = []
        for item in detail:
            if isinstance(item, dict):
                message = item.get("msg", "Invalid value")
                location = item.get("loc", [])
                field = location[-1] if location else "field"
                parts.append(f"{field}: {message}")
        if parts:
            return " ".join(parts)
    return f"The API returned HTTP {response.status_code}."


def api_request(
    method: str,
    path: str,
    payload: dict | None = None,
    timeout: int = 30,
    token: str | None = None,
):
    """Call one API path. Returns the JSON body, or None and an error sentence."""
    headers = {"Authorization": f"Bearer {token}"} if token else None
    base_url = api_base_url()
    try:
        response = requests.request(
            method,
            f"{base_url}{path}",
            json=payload,
            headers=headers,
            timeout=timeout,
        )
    except requests.RequestException:
        return None, f"Cannot reach the API at {base_url}. Start FastAPI on port 8001 and try again."
    if response.status_code >= 400:
        return None, error_text(response)
    if not response.content:
        return {}, None
    return response.json(), None


def api_upload(path: str, filename: str, content: bytes, token: str | None = None, timeout: int = 60):
    """Post one PDF. The body is file bytes, not JSON, and it is not printed."""
    headers = {"Authorization": f"Bearer {token}"} if token else None
    base_url = api_base_url()
    try:
        response = requests.request(
            "POST",
            f"{base_url}{path}",
            files={"file": (filename, content, "application/pdf")},
            headers=headers,
            timeout=timeout,
        )
    except requests.RequestException:
        return None, f"Cannot reach the API at {base_url}. Start FastAPI on port 8001 and try again."
    if response.status_code >= 400:
        return None, error_text(response)
    if not response.content:
        return {}, None
    return response.json(), None
