"""Login, sign up, and account setup screens."""

import math
import re
import time

import streamlit as st

from api import api_request
from auth_session import store_login
from components import page_header, select_page

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
OTP_RESEND_SECONDS = 60
OTP_REQUEST_ACCEPTED = (
    "If an eligible profile exists, a verification code has been sent to the registered email address."
)


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
    done = st.session_state.pop("auth_success", None)
    if done:
        st.success(done)


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


def _seconds_until(sent_key: str) -> int:
    """Return how long another code request must wait. The first request is not delayed."""
    sent_at = st.session_state.get(sent_key)
    if not isinstance(sent_at, (int, float)):
        return 0
    remaining = OTP_RESEND_SECONDS - (time.time() - float(sent_at))
    if remaining <= 0:
        return 0
    return math.ceil(remaining)


def _seconds_until_resend() -> int:
    return _seconds_until("setup_otp_sent_at")


def _submit_send_otp() -> None:
    email = str(st.session_state.get("setup_email") or "")
    problem = _email_problem(email)
    if problem:
        st.session_state.auth_notice = problem
        return
    remaining = _seconds_until_resend()
    if st.session_state.get("setup_otp_requested") and remaining > 0:
        st.session_state.auth_notice = f"Resend temporarily unavailable. Wait {remaining} seconds."
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
    st.session_state.setup_otp_sent_at = time.time()
    detail = body.get("detail")
    st.session_state.setup_notice = detail.strip() if isinstance(detail, str) and detail.strip() else OTP_REQUEST_ACCEPTED
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
    st.session_state.setup_otp_sent_at = None
    store_login(body["token"], candidate)
    st.session_state.nav = "My Profile"
    st.toast("Password successfully set.")


def _submit_change_password() -> None:
    current = str(st.session_state.get("change_current") or "")
    new_password = str(st.session_state.get("change_new") or "")
    confirm = str(st.session_state.get("change_confirm") or "")
    st.session_state.change_current = ""
    st.session_state.change_new = ""
    st.session_state.change_confirm = ""
    if not current:
        st.session_state.change_notice = "Enter your current password."
        return
    problem = _password_problem(new_password, confirm)
    if problem:
        st.session_state.change_notice = problem
        return
    _body, error = api_request(
        "POST",
        "/auth/change-password",
        {"current_password": current, "new_password": new_password},
        token=st.session_state.get("auth_token"),
    )
    if error:
        st.session_state.change_notice = error
        return
    st.session_state.change_success = "Password updated."


def _submit_forgot_send() -> None:
    email = str(st.session_state.get("forgot_email") or "")
    problem = _email_problem(email)
    if problem:
        st.session_state.auth_notice = problem
        return
    remaining = _seconds_until("forgot_otp_sent_at")
    if st.session_state.get("forgot_otp_requested") and remaining > 0:
        st.session_state.auth_notice = f"Resend temporarily unavailable. Wait {remaining} seconds."
        return
    body, error = api_request(
        "POST",
        "/auth/password-reset/send-otp",
        {"email": email.strip().lower()},
    )
    if error or not isinstance(body, dict):
        st.session_state.auth_notice = error or "Email delivery is temporarily unavailable."
        return
    st.session_state.forgot_otp_requested = True
    st.session_state.forgot_otp_sent_at = time.time()
    detail = body.get("detail")
    st.session_state.forgot_notice = detail.strip() if isinstance(detail, str) and detail.strip() else OTP_REQUEST_ACCEPTED
    dev_otp = body.get("dev_otp")
    st.session_state.forgot_dev_otp = dev_otp if isinstance(dev_otp, str) and dev_otp.isdigit() and len(dev_otp) == 6 else ""


def _submit_forgot_reset() -> None:
    email = str(st.session_state.get("forgot_email") or "")
    new_password = str(st.session_state.get("forgot_password") or "")
    confirm = str(st.session_state.get("forgot_confirm") or "")
    otp = str(st.session_state.get("forgot_otp") or "").strip()
    st.session_state.forgot_password = ""
    st.session_state.forgot_confirm = ""
    if not st.session_state.get("forgot_otp_requested"):
        st.session_state.auth_notice = "Send a verification code first."
        return
    if not otp.isdigit() or len(otp) != 6:
        st.session_state.auth_notice = "Enter the six-digit verification code."
        return
    problem = _email_problem(email) or _password_problem(new_password, confirm)
    if problem:
        st.session_state.auth_notice = problem
        return
    _body, error = api_request(
        "POST",
        "/auth/password-reset/confirm",
        {
            "email": email.strip().lower(),
            "otp": otp,
            "new_password": new_password,
        },
    )
    if error:
        st.session_state.auth_notice = error or "The password could not be saved."
        return
    _clear_forgot_state()
    st.session_state.auth_success = "Password updated. Log in with the new password."
    st.session_state.nav = "Login"


def _clear_forgot_state() -> None:
    for key in ("forgot_otp", "forgot_password", "forgot_confirm", "forgot_dev_otp", "forgot_notice"):
        st.session_state[key] = ""
    st.session_state.forgot_otp_requested = False
    st.session_state.forgot_otp_sent_at = None


def _return_to_login() -> None:
    _clear_forgot_state()
    select_page("Login")


def render_change_password() -> None:
    """Ask the signed-in user for the current password before replacing it."""
    error = st.session_state.pop("change_notice", None)
    done = st.session_state.pop("change_success", None)
    if error:
        st.error(error)
    if done:
        st.success(done)
    with st.container(border=True):
        st.markdown(
            (
                "<div class='password-form'></div>"
                "<p class='section-label'>Change password</p>"
                "<p class='form-hint'>Enter the current password, then a new password of 8 to 128 characters, "
                "and confirm it. Other signed-in browsers will need to log in again. This session stays signed in.</p>"
            ),
            unsafe_allow_html=True,
        )
        st.text_input("Current password", key="change_current", type="password", max_chars=128)
        st.text_input("New password", key="change_new", type="password", max_chars=128)
        st.text_input("Confirm new password", key="change_confirm", type="password", max_chars=128)
        st.button("Update password", on_click=_submit_change_password)


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
                "A profile without a password uses Account setup to verify the email. "
                "Forgot password is for an account that already has one.</p>"
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
        st.button("Forgot password", on_click=select_page, args=("Forgot password",))


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
                "<p class='form-hint'>Use 8 to 128 characters, then enter the same password again. "
                "You can add skills and preferences after this.</p>"
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
                "<p class='form-hint'>1. Enter the registered email. 2. Request a code. "
                "3. Enter the six-digit code. 4. Set a password of 8 to 128 characters. "
                "5. Confirm it. The code expires in 10 minutes and can be requested again after 60 seconds.</p>"
                f"<p class='status-line'>{_status_line(status, status_error)}</p>"
            ),
            unsafe_allow_html=True,
        )
        st.text_input("Email", key="setup_email", placeholder="name@example.com")
        st.button("Send OTP", type="primary", on_click=_submit_send_otp)
        if st.session_state.get("setup_otp_requested"):
            remaining = _seconds_until_resend()
            wait = f" Resend is available in {remaining} seconds." if remaining else " Another code can be requested after 60 seconds."
            st.markdown(
                "<p class='form-hint'>The code expires in 10 minutes."
                f"{wait}</p>",
                unsafe_allow_html=True,
            )
            st.text_input("Verification code", key="setup_otp", max_chars=6)
            st.button("Resend OTP", on_click=_submit_send_otp)
            st.text_input("New password", key="setup_password", type="password", max_chars=128)
            st.text_input("Confirm new password", key="setup_confirm", type="password", max_chars=128)
            st.button("Set password", type="primary", on_click=_submit_setup)
        st.markdown("<p class='auth-switch'>Ready to sign in?</p>", unsafe_allow_html=True)
        st.button("Back to login", on_click=select_page, args=("Login",))


def page_forgot(status: dict | None, status_error: str | None) -> None:
    """Reset a password for an account that already has one."""
    page_header(
        "Reset your password",
        "Use the email on an account that already has a password.",
        "Account",
    )
    _show_notice()
    sent = st.session_state.get("forgot_notice")
    if sent:
        st.success(sent)
    dev_otp = str(st.session_state.get("forgot_dev_otp") or "")
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
                "<p class='section-label auth-card'>Forgot password</p>"
                "<p class='form-hint'>1. Enter the account email. 2. Request a code. "
                "3. Enter the six-digit code. 4. Choose a new password of 8 to 128 characters. "
                "5. Confirm it. A successful reset returns you to login. "
                "The code expires in 10 minutes and can be requested again after 60 seconds.</p>"
                f"<p class='status-line'>{_status_line(status, status_error)}</p>"
            ),
            unsafe_allow_html=True,
        )
        st.text_input("Email", key="forgot_email", placeholder="name@example.com")
        st.button("Send OTP", type="primary", on_click=_submit_forgot_send)
        if st.session_state.get("forgot_otp_requested"):
            remaining = _seconds_until("forgot_otp_sent_at")
            wait = f" Resend is available in {remaining} seconds." if remaining else " Another code can be requested after 60 seconds."
            st.markdown(
                f"<p class='form-hint'>The code expires in 10 minutes.{wait}</p>",
                unsafe_allow_html=True,
            )
            st.text_input("Verification code", key="forgot_otp", max_chars=6)
            st.button("Resend OTP", on_click=_submit_forgot_send)
            st.text_input("New password", key="forgot_password", type="password", max_chars=128)
            st.text_input("Confirm new password", key="forgot_confirm", type="password", max_chars=128)
            st.button("Reset password", type="primary", on_click=_submit_forgot_reset)
        st.markdown("<p class='auth-switch'>Remembered it?</p>", unsafe_allow_html=True)
        st.button("Back to login", on_click=_return_to_login)
