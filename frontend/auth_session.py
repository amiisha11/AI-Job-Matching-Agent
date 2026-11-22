"""Keep the signed-in profile in the Streamlit session.

The password is never written here. The session stores the token returned by
the API and the profile fields needed to reopen the same account.
"""

import streamlit as st

from api import api_request
from session_cookie import COOKIE_NAME, cookie_script

PUBLIC_PAGES = ["Login", "Sign Up", "Account setup"]
APP_PAGES = ["Home", "My Profile", "Discover Jobs", "Match Insights", "Saved Jobs", "Resume Centre"]
LOGIN_AGAIN = {"Log in to continue.", "Your session has expired. Log in again."}
PROFILE_WIDGET_KEYS = (
    "profile_name",
    "profile_email",
    "profile_education",
    "custom_education",
    "profile_years",
    "profile_skills",
    "profile_roles",
    "profile_locations",
    "skill_choices",
    "role_choices",
    "location_choices",
    "custom_skill",
    "custom_role",
    "custom_location",
    "skill_notice",
    "role_notice",
    "location_notice",
    "profile_degree",
    "custom_degree",
    "profile_field",
    "custom_field",
    "profile_specialization",
    "profile_institution",
    "profile_graduation",
    "profile_industries",
    "profile_countries",
    "profile_remote",
    "profile_builder_step",
    "profile_draft",
    "builder_catalogue",
    "_profile_form_ready",
)


def read_browser_token() -> str:
    """Read the session cookie. A missing cookie is a logged-out visit."""
    try:
        value = st.context.cookies.get(COOKIE_NAME, "")
    except Exception:
        return ""
    if not isinstance(value, str):
        return ""
    return value.strip()


def store_login(token: str, candidate: dict) -> None:
    """Remember the session and profile. Password fields are not copied."""
    safe = {
        key: value
        for key, value in candidate.items()
        if "password" not in key and "token" not in key and "hash" not in key
    }
    st.session_state.auth_token = token
    st.session_state.candidate_id = safe.get("id")
    st.session_state.candidate_name = safe.get("name") or ""
    st.session_state.profile = safe
    st.session_state.matches = None
    st.session_state.saved_jobs = None
    st.session_state.job_catalog = None
    st.session_state.discover_filters = None
    st.session_state.discover_results = None
    st.session_state.preparation_cache = None
    st.session_state.selected_job_id = None
    _clear_preparation_widgets()
    _clear_resume_state()
    st.session_state._cookie_set = False
    st.session_state._reset_profile_form = True


def clear_local_session() -> None:
    """Drop the local session and ask the browser cookie to be cleared."""
    st.session_state.auth_token = None
    st.session_state.candidate_id = None
    st.session_state.candidate_name = ""
    st.session_state.profile = None
    st.session_state.matches = None
    st.session_state.saved_jobs = None
    st.session_state.job_catalog = None
    st.session_state.discover_filters = None
    st.session_state.discover_results = None
    st.session_state.preparation_cache = None
    st.session_state.selected_job_id = None
    _clear_preparation_widgets()
    _clear_resume_state()
    st.session_state._cookie_set = False
    st.session_state._clear_cookie = True
    st.session_state._reset_profile_form = True
    for key in (
        "setup_claim",
        "setup_otp",
        "setup_password",
        "setup_confirm",
        "setup_dev_otp",
        "setup_notice",
        "login_password",
        "signup_password",
        "signup_confirm",
    ):
        if key in st.session_state:
            st.session_state[key] = ""
    if "setup_otp_requested" in st.session_state:
        st.session_state.setup_otp_requested = False


def _clear_resume_state() -> None:
    """Drop extracted resume text so the next account cannot see it."""
    st.session_state.resume = None
    st.session_state.resume_match = None
    st.session_state.resume_signature = None
    st.session_state.resume_error = None
    st.session_state.resume_uploader = int(st.session_state.get("resume_uploader") or 0) + 1
    for key in list(st.session_state.keys()):
        if str(key).startswith(("resume-file-", "resume-job", "resume-improve-")) or key == "resume-section":
            del st.session_state[key]


def _clear_preparation_widgets() -> None:
    """Drop journal widgets so the next account does not see the previous plan."""
    for key in list(st.session_state.keys()):
        if str(key).startswith("prep-"):
            del st.session_state[key]


def reset_profile_form() -> None:
    """Clear profile widgets before they are drawn again."""
    if not st.session_state.pop("_reset_profile_form", False):
        return
    for key in PROFILE_WIDGET_KEYS:
        if key in st.session_state:
            del st.session_state[key]


def logout() -> None:
    """Delete the server session, then clear this browser."""
    token = st.session_state.get("auth_token")
    if token:
        api_request("POST", "/auth/logout", token=token)
    clear_local_session()
    st.session_state.nav = "Login"


def restore_session() -> str | None:
    """Load the profile from the browser cookie once per signed-out visit."""
    if st.session_state.get("auth_token") or st.session_state.get("_clear_cookie"):
        return None
    token = read_browser_token()
    if not token:
        return None
    body, error = api_request("GET", "/auth/me", token=token)
    if error or not isinstance(body, dict) or "id" not in body:
        st.session_state._clear_cookie = True
        return error or "Log in to continue."
    store_login(token, body)
    st.session_state._cookie_set = True
    return None


def apply_page_gate() -> None:
    """Keep signed-out visitors on the account pages."""
    if st.session_state.pop("_force_login", False):
        st.session_state.nav = "Login"
    logged_in = bool(st.session_state.get("auth_token") and st.session_state.get("candidate_id"))
    nav = st.session_state.get("nav")
    if logged_in and nav in PUBLIC_PAGES:
        st.session_state.nav = "Home"
    if not logged_in and nav not in PUBLIC_PAGES:
        st.session_state.nav = "Login"


def sync_session_cookie() -> None:
    """Write or clear the browser cookie without printing the token."""
    import streamlit.components.v1 as components

    if st.session_state.pop("_clear_cookie", False):
        components.html(cookie_script(""), height=0)
        return
    token = st.session_state.get("auth_token")
    if token and not st.session_state.get("_cookie_set"):
        components.html(cookie_script(token), height=0)
        st.session_state._cookie_set = True


def authed_request(method: str, path: str, payload: dict | None = None, timeout: int = 30):
    """Call a profile route with the session token."""
    body, error = api_request(
        method,
        path,
        payload,
        timeout=timeout,
        token=st.session_state.get("auth_token"),
    )
    if error in LOGIN_AGAIN:
        clear_local_session()
        st.session_state.auth_notice = error
        st.session_state._force_login = True
        st.rerun()
    return body, error


def authed_upload(path: str, filename: str, content: bytes, timeout: int = 60):
    """Upload one file with the session token. The file bytes are not logged."""
    from api import api_upload

    body, error = api_upload(
        path,
        filename,
        content,
        token=st.session_state.get("auth_token"),
        timeout=timeout,
    )
    if error in LOGIN_AGAIN:
        clear_local_session()
        st.session_state.auth_notice = error
        st.session_state._force_login = True
        st.rerun()
    return body, error
