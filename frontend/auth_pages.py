"""Login, sign up, and account setup screens."""

import re

import streamlit as st

from api import api_request
from auth_session import store_login
from components import page_header, select_page

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _password_problem(password: str, confirm: str | None = None) -> str | None:
    if len(password) < 8:
        return "Use at least 8 characters."
    if len(password) > 128:
        return "Use at most 128 characters."
    if confirm is not None and password != confirm:
        return "Passwords do not match."
    return None


def _email_problem(email: str) -> str | None:
    if not _EMAIL_PATTERN.fullmatch(email.strip().lower()):
        return "Enter an email address like name@example.com."
    return None


def _show_notice() -> None:
    notice = st.session_state.pop("auth_notice", None)
    if notice:
        st.error(notice)


def _status_line(status: dict | None, status_error: str | None) -> str:
    if status_error:
        return "The local API is not reachable."
    if isinstance(status, dict) and status.get("message"):
        return str(status["message"])
    return "API is running."


def _submit_login() -> None:
    email = str(st.session_state.get("login_email") or "")
    password = str(st.session_state.get("login_password") or "")
    st.session_state.login_password = ""
    problem = _email_problem(email) or _password_problem(password)
    if problem:
        st.session_state.auth_notice = problem
        return
    body, error = api_request(
        "POST",
        "/auth/login",
        {"email": email.strip().lower(), "password": password},
    )
    candidate = body.get("candidate") if isinstance(body, dict) else None
    if error or not isinstance(candidate, dict) or not body.get("token") or not candidate.get("id"):
        st.session_state.auth_notice = error or "Incorrect email or password."
        return
    store_login(body["token"], candidate)
    st.session_state.nav = "Home"


def _submit_signup() -> None:
    name = str(st.session_state.get("signup_name") or "")
    email = str(st.session_state.get("signup_email") or "")
    password = str(st.session_state.get("signup_password") or "")
    confirm = str(st.session_state.get("signup_confirm") or "")
    st.session_state.signup_password = ""
    st.session_state.signup_confirm = ""
    if not " ".join(name.split()):
        st.session_state.auth_notice = "Enter your name."
        return
    problem = _email_problem(email) or _password_problem(password, confirm)
    if problem:
        st.session_state.auth_notice = problem
        return
    body, error = api_request(
        "POST",
        "/auth/register",
        {
            "name": " ".join(name.split()),
            "email": email.strip().lower(),
            "password": password,
        },
    )
    candidate = body.get("candidate") if isinstance(body, dict) else None
    if error or not isinstance(candidate, dict) or not body.get("token") or not candidate.get("id"):
        st.session_state.auth_notice = error or "The account could not be created."
        return
    store_login(body["token"], candidate)
    st.session_state.nav = "My Profile"


def _submit_send_otp() -> None:
    email = str(st.session_state.get("setup_email") or "")
    problem = _email_problem(email)
    if problem:
        st.session_state.auth_notice = problem
        return
    body, error = api_request(
        "POST",
        "/auth/setup/send-otp",
        {"email": email.strip().lower()},
    )
    if error or not isinstance(body, dict):
        st.session_state.auth_notice = error or "Email delivery is temporarily unavailable."
        return
    st.session_state.setup_otp_requested = True
    st.session_state.setup_notice = (
        "Verification code sent. It expires in 10 minutes. "
        "If an eligible profile exists, the code was sent to that email address."
    )
    dev_otp = body.get("dev_otp")
    st.session_state.setup_dev_otp = dev_otp if isinstance(dev_otp, str) and dev_otp.isdigit() and len(dev_otp) == 6 else ""


def _submit_setup() -> None:
    email = str(st.session_state.get("setup_email") or "")
    password = str(st.session_state.get("setup_password") or "")
    confirm = str(st.session_state.get("setup_confirm") or "")
    otp = str(st.session_state.get("setup_otp") or "").strip()
    st.session_state.setup_password = ""
    st.session_state.setup_confirm = ""
    if not st.session_state.get("setup_otp_requested"):
        st.session_state.auth_notice = "Send a verification code first."
        return
    if not otp.isdigit() or len(otp) != 6:
        st.session_state.auth_notice = "Enter the six-digit verification code."
        return
    problem = _email_problem(email) or _password_problem(password, confirm)
    if problem:
        st.session_state.auth_notice = problem
        return
    body, error = api_request(
        "POST",
        "/auth/setup-password",
        {
            "email": email.strip().lower(),
            "password": password,
            "otp": otp,
        },
    )
    candidate = body.get("candidate") if isinstance(body, dict) else None
    if error or not isinstance(candidate, dict) or not body.get("token") or not candidate.get("id"):
        st.session_state.auth_notice = error or "The password could not be saved."
        return
    st.session_state.setup_otp = ""
    st.session_state.setup_dev_otp = ""
    st.session_state.setup_notice = ""
    st.session_state.setup_otp_requested = False
    store_login(body["token"], candidate)
    st.session_state.nav = "My Profile"
    st.toast("Password successfully set.")


def page_login(status: dict | None, status_error: str | None) -> None:
    """Ask for the email and password of an existing account."""
    page_header(
        "Welcome back",
        "Log in to open the profile, matches, and saved jobs already on your account.",
        "Account",
    )
    _show_notice()
    with st.container(border=True):
        st.markdown(
            (
                "<div class='auth-brand'><span class='sidebar-mark'>AJ</span><span>AI Job Matching</span></div>"
                "<p class='section-label auth-card'>Sign in</p>"
                "<p class='form-hint'>Use the email and password from Sign Up. "
                "A profile without a password uses Account setup to verify the email.</p>"
                f"<p class='status-line'>{_status_line(status, status_error)}</p>"
            ),
            unsafe_allow_html=True,
        )
        st.text_input("Email", key="login_email", placeholder="name@example.com")
        st.text_input("Password", key="login_password", type="password", max_chars=128)
        st.button("Log in", type="primary", on_click=_submit_login)
        st.markdown("<p class='auth-switch'>Or continue another way</p>", unsafe_allow_html=True)
        create_col, setup_col = st.columns(2, gap="small")
        with create_col:
            st.button("Create an account", on_click=select_page, args=("Sign Up",))
        with setup_col:
            st.button("Set a password for an existing profile", on_click=select_page, args=("Account setup",))


def page_signup(status: dict | None, status_error: str | None) -> None:
    """Create an account, a profile, and a session."""
    page_header(
        "Create your account",
        "Choose a password. Your profile is saved for the next visit.",
        "Account",
    )
    _show_notice()
    with st.container(border=True):
        st.markdown(
            (
                "<div class='auth-brand'><span class='sidebar-mark'>AJ</span><span>AI Job Matching</span></div>"
                "<p class='section-label auth-card'>Sign up</p>"
                "<p class='form-hint'>Use at least 8 characters. You can add skills and preferences after this.</p>"
                f"<p class='status-line'>{_status_line(status, status_error)}</p>"
            ),
            unsafe_allow_html=True,
        )
        st.text_input("Name", key="signup_name")
        st.text_input("Email", key="signup_email", placeholder="name@example.com")
        st.text_input("Password", key="signup_password", type="password", max_chars=128)
        st.text_input("Confirm password", key="signup_confirm", type="password", max_chars=128)
        st.button("Create account", type="primary", on_click=_submit_signup)
        st.markdown("<p class='auth-switch'>Already registered?</p>", unsafe_allow_html=True)
        st.button("I already have an account", on_click=select_page, args=("Login",))


def page_setup(status: dict | None, status_error: str | None) -> None:
    """Verify an existing passwordless profile by email, then set a password."""
    page_header(
        "Set a password",
        "Use this only when your email already has a profile and that profile has no password yet.",
        "Account",
    )
    _show_notice()
    sent = st.session_state.get("setup_notice")
    if sent:
        st.success(sent)
    dev_otp = str(st.session_state.get("setup_dev_otp") or "")
    if dev_otp:
        st.warning(
            "Development only. Email delivery is not configured, so the code is shown here and was not sent. "
            "This does not appear when the app is running in production."
        )
        st.code(dev_otp)
    with st.container(border=True):
        st.markdown(
            (
                "<div class='auth-brand'><span class='sidebar-mark'>AJ</span><span>AI Job Matching</span></div>"
                "<p class='section-label auth-card'>Account setup</p>"
                "<p class='form-hint'>Enter the email on the existing profile. "
                "A six-digit code confirms that you can read that inbox.</p>"
                f"<p class='status-line'>{_status_line(status, status_error)}</p>"
            ),
            unsafe_allow_html=True,
        )
        st.text_input("Email", key="setup_email", placeholder="name@example.com")
        st.button("Send OTP", type="primary", on_click=_submit_send_otp)
        if st.session_state.get("setup_otp_requested"):
            st.markdown(
                "<p class='form-hint'>The code expires in 10 minutes. "
                "You can request another code 60 seconds after the last request.</p>",
                unsafe_allow_html=True,
            )
            st.text_input("Verification code", key="setup_otp", max_chars=6)
            st.button("Resend OTP", on_click=_submit_send_otp)
            st.text_input("New password", key="setup_password", type="password", max_chars=128)
            st.text_input("Confirm new password", key="setup_confirm", type="password", max_chars=128)
            st.button("Set password", type="primary", on_click=_submit_setup)
        st.markdown("<p class='auth-switch'>Ready to sign in?</p>", unsafe_allow_html=True)
        st.button("Back to login", on_click=select_page, args=("Login",))
