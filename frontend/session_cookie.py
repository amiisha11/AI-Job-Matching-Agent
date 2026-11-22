"""Build the browser-cookie script for a session token.

The token is not a password. HttpOnly cannot be set from this page script,
so the cookie is SameSite=Lax and is never placed in the address bar.
"""

import json

from app_config import cookie_secure_enabled

COOKIE_NAME = "aj_session"
MAX_AGE_SECONDS = 12 * 60 * 60


def cookie_is_secure() -> bool:
    """True when COOKIE_SECURE asks the browser to send the cookie only over HTTPS."""
    return cookie_secure_enabled()


def cookie_assignment(token: str) -> str:
    """Return the cookie text. An empty token clears the cookie."""
    secure = "; Secure" if cookie_is_secure() else ""
    if token:
        return f"{COOKIE_NAME}={token}; Path=/; Max-Age={MAX_AGE_SECONDS}; SameSite=Lax{secure}"
    return f"{COOKIE_NAME}=; Path=/; Max-Age=0; SameSite=Lax{secure}"


def cookie_script(token: str) -> str:
    """Return a same-origin script that sets the cookie on the Streamlit page."""
    assignment = json.dumps(cookie_assignment(token))
    return f"<script>window.parent.document.cookie = {assignment};</script>"
