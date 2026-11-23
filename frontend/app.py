"""Streamlit screen for the local job-matching demo.

This file talks only to the FastAPI backend. It does not open the database
and it does not call Gemini.
"""

import sys
from pathlib import Path

import streamlit as st

FRONTEND_DIR = Path(__file__).resolve().parent
if str(FRONTEND_DIR) not in sys.path:
    sys.path.insert(0, str(FRONTEND_DIR))

from api import api_request
from auth_pages import page_forgot, page_login, page_setup, page_signup
from auth_session import apply_page_gate, reset_profile_form, restore_session, sync_session_cookie
from components import render_sidebar
from pages import page_discover, page_home, page_matches, page_profile, page_saved
from resume_centre import page_resume
from theme import inject_theme

st.set_page_config(
    page_title="AI Job Matching Agent",
    page_icon="💼",
    layout="wide",
    menu_items={
        "Get help": "https://github.com/amiisha11/AI-Job-Matching-Agent",
        "Report a bug": None,
        "About": (
            "AI Job Matching Agent. Choose System, Light, or Dark from this menu. "
            "The source is on GitHub."
        ),
    },
)

for key, value in {
    "candidate_id": None,
    "candidate_name": "",
    "profile": None,
    "matches": None,
    "saved_jobs": None,
    "job_catalog": None,
    "preparation_cache": None,
    "resume": None,
    "resume_match": None,
    "resume_signature": None,
    "resume_error": None,
    "resume_uploader": 0,
    "nav": "Login",
    "auth_token": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = value

inject_theme()
auth_error = restore_session()
if auth_error:
    st.session_state.auth_notice = auth_error
apply_page_gate()
reset_profile_form()
sync_session_cookie()
status, status_error = api_request("GET", "/")
page = render_sidebar(api_ok=status_error is None)

if status_error:
    st.error(status_error)

if page == "Login":
    page_login(status, status_error)
elif page == "Sign Up":
    page_signup(status, status_error)
elif page == "Account setup":
    page_setup(status, status_error)
elif page == "Forgot password":
    page_forgot(status, status_error)
else:
    pages = {
        "Home": lambda: page_home(status, status_error),
        "My Profile": page_profile,
        "Discover Jobs": page_discover,
        "Match Insights": page_matches,
        "Saved Jobs": page_saved,
        "Resume Centre": page_resume,
    }
    pages[page]()
