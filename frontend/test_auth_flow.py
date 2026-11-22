"""Login, sign up, setup, and logout with a mocked API. No database writes."""

import json
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

FRONTEND_DIR = Path(__file__).resolve().parent
if str(FRONTEND_DIR) not in sys.path:
    sys.path.insert(0, str(FRONTEND_DIR))

from session_cookie import cookie_is_secure, cookie_script

APP_PATH = Path(__file__).resolve().parent / "app.py"
SECRET = "correct-horse"
CANDIDATE = {
    "id": 9,
    "name": "Ada Lovelace",
    "email": "ada@example.com",
    "education": None,
    "skills": [],
    "preferred_roles": [],
    "preferred_locations": [],
    "years_experience": 0,
}


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.status_code = status_code
        self._payload = payload
        self.content = b"" if status_code == 204 else json.dumps(payload).encode()

    def json(self):
        return self._payload


def _labeled(widgets, label):
    return next(widget for widget in widgets if widget.label == label)


def _session_text(app) -> str:
    return "\n".join(str(app.session_state[key]) for key in app.session_state)


@contextmanager
def _mocked_auth(page="Login", **state):
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append((method, url, kwargs.get("json"), kwargs.get("headers")))
        if method == "POST" and url.endswith("/auth/login"):
            if kwargs["json"]["password"] != SECRET:
                return FakeResponse({"detail": "Incorrect email or password."}, 401)
            return FakeResponse({"token": "issued-token", "candidate": CANDIDATE})
        if method == "POST" and url.endswith("/auth/register"):
            if kwargs["json"]["email"] == "ada@example.com":
                return FakeResponse(
                    {"detail": "An account with this email already exists. Log in instead."},
                    409,
                )
            return FakeResponse({"token": "issued-token", "candidate": CANDIDATE}, 201)
        if method == "POST" and url.endswith("/auth/setup/send-otp"):
            return FakeResponse(
                {"detail": "If an eligible profile exists, a verification code has been sent to the registered email address."}
            )
        if method == "POST" and url.endswith("/auth/setup-password"):
            if kwargs["json"].get("otp") != "123456":
                return FakeResponse({"detail": "The verification code is not valid."}, 401)
            return FakeResponse({"token": "issued-token", "candidate": CANDIDATE})
        if method == "POST" and url.endswith("/auth/logout"):
            return FakeResponse({}, 204)
        if method == "GET" and url.endswith("/saved-jobs"):
            if page == "Saved Jobs":
                return FakeResponse({"detail": "Your session has expired. Log in again."}, 401)
            return FakeResponse([])
        if method == "GET" and (url.endswith("/jobs/") or url.endswith("/matches")):
            return FakeResponse([])
        if method == "GET" and url.endswith(":8001/"):
            return FakeResponse({"status": "ok", "message": "API is running."})
        raise AssertionError(f"Unexpected API call {method} {url}")

    def reject_session_request(*args, **kwargs):
        raise AssertionError("Session.request was called; the mock did not intercept it.")

    with (
        patch("requests.request", fake_request),
        patch("requests.sessions.Session.request", reject_session_request),
    ):
        app = AppTest.from_file(str(APP_PATH))
        app.session_state["nav"] = page
        for key, value in state.items():
            app.session_state[key] = value
        app.run()
        assert not app.exception, app.exception
        yield app, calls


def test_cookie_script_sets_and_clears_without_a_password():
    created = cookie_script("issued-token")
    assert "issued-token" in created
    assert "Max-Age=43200" in created
    assert "SameSite=Lax" in created
    assert "Max-Age=0" in cookie_script("")
    assert SECRET not in created
    with (
        patch.dict("os.environ", {"COOKIE_SECURE": ""}, clear=False),
        patch("app_config.streamlit_secret", return_value=None),
    ):
        local_cookie = cookie_script("issued-token")
    assert "Secure" not in local_cookie
    assert "SameSite=Lax" in local_cookie
    with patch.dict("os.environ", {"COOKIE_SECURE": "true"}):
        assert cookie_is_secure()
        assert cookie_script("issued-token").endswith('Secure";</script>') or "Secure" in cookie_script("issued-token")


def test_login_signup_and_setup_keep_the_password_out_of_session():
    with _mocked_auth() as (login, calls):
        _labeled(login.text_input, "Email").set_value("ada@example.com")
        _labeled(login.text_input, "Password").set_value("short")
        _labeled(login.button, "Log in").click().run()
        assert any("8 characters" in item.value for item in login.error)
        assert not any(url.endswith("/auth/login") for _, url, _, _ in calls)
        assert login.session_state["login_password"] == ""

        _labeled(login.text_input, "Email").set_value("ada@example.com")
        _labeled(login.text_input, "Password").set_value("wrong-horse")
        _labeled(login.button, "Log in").click().run()
        assert any("Incorrect email or password." in item.value for item in login.error)
        assert login.session_state["login_password"] == ""
        assert login.session_state["auth_token"] is None
        assert SECRET not in _session_text(login)

        _labeled(login.text_input, "Email").set_value("Ada@Example.com")
        _labeled(login.text_input, "Password").set_value(SECRET)
        _labeled(login.button, "Log in").click().run()
        assert login.session_state["auth_token"] == "issued-token"
        assert login.session_state["candidate_id"] == 9
        assert login.session_state["nav"] == "Home"
        assert SECRET not in _session_text(login)
        login_call = next(call for call in calls if call[0] == "POST" and call[1].endswith("/auth/login"))
        assert login_call[2]["email"] == "ada@example.com"
        assert not (login_call[3] or {}).get("Authorization")

    with _mocked_auth("Sign Up") as (signup, calls):
        _labeled(signup.text_input, "Name").set_value("Grace Hopper")
        _labeled(signup.text_input, "Email").set_value("ada@example.com")
        _labeled(signup.text_input, "Password").set_value(SECRET)
        _labeled(signup.text_input, "Confirm password").set_value(SECRET)
        _labeled(signup.button, "Create account").click().run()
        assert any("already exists" in item.value for item in signup.error)
        assert signup.session_state["auth_token"] is None
        assert signup.session_state["signup_password"] == ""
        assert SECRET not in _session_text(signup)

        _labeled(signup.text_input, "Email").set_value("grace@example.com")
        _labeled(signup.text_input, "Password").set_value(SECRET)
        _labeled(signup.text_input, "Confirm password").set_value("different")
        _labeled(signup.button, "Create account").click().run()
        assert any("do not match" in item.value for item in signup.error)
        assert not any(call[2] and call[2].get("email") == "grace@example.com" for call in calls)

        _labeled(signup.text_input, "Password").set_value(SECRET)
        _labeled(signup.text_input, "Confirm password").set_value(SECRET)
        _labeled(signup.button, "Create account").click().run()
        assert signup.session_state["candidate_id"] == 9
        assert signup.session_state["nav"] == "My Profile"
        assert SECRET not in _session_text(signup)

    with _mocked_auth("Account setup") as (setup, calls):
        _labeled(setup.button, "Send OTP").click().run()
        assert any("email" in item.value.casefold() for item in setup.error)
        assert not any(url.endswith("/auth/setup/send-otp") for _, url, _, _ in calls)

        _labeled(setup.text_input, "Email").set_value("ada@example.com")
        _labeled(setup.button, "Send OTP").click().run()
        assert any("Verification code sent" in item.value for item in setup.success)
        _labeled(setup.text_input, "Verification code").set_value("123456")
        _labeled(setup.text_input, "New password").set_value(SECRET)
        _labeled(setup.text_input, "Confirm new password").set_value("different")
        _labeled(setup.button, "Set password").click().run()
        assert any("do not match" in item.value for item in setup.error)
        assert setup.session_state["auth_token"] is None

        _labeled(setup.text_input, "Verification code").set_value("000000")
        _labeled(setup.text_input, "New password").set_value(SECRET)
        _labeled(setup.text_input, "Confirm new password").set_value(SECRET)
        _labeled(setup.button, "Set password").click().run()
        assert any("not valid" in item.value for item in setup.error)

        _labeled(setup.text_input, "Verification code").set_value("123456")
        _labeled(setup.text_input, "New password").set_value(SECRET)
        _labeled(setup.text_input, "Confirm new password").set_value(SECRET)
        _labeled(setup.button, "Set password").click().run()
        assert setup.session_state["candidate_id"] == 9
        assert setup.session_state["profile"]["email"] == "ada@example.com"
        assert setup.session_state["setup_otp"] == ""
        assert SECRET not in _session_text(setup)


def test_logout_and_expired_session_return_to_login():
    with _mocked_auth(
        "Home",
        auth_token="issued-token",
        candidate_id=9,
        candidate_name="Ada Lovelace",
        profile=CANDIDATE,
        setup_otp="123456",
        setup_dev_otp="123456",
        setup_password=SECRET,
    ) as (home, calls):
        _labeled(home.button, "Log out").click().run()
        assert home.session_state["auth_token"] is None
        assert home.session_state["setup_otp"] == ""
        assert home.session_state["setup_dev_otp"] == ""
        assert home.session_state["setup_password"] == ""
        assert home.session_state["candidate_id"] is None
        assert home.session_state["nav"] == "Login"
        assert any(url.endswith("/auth/logout") for _, url, _, _ in calls)
        assert SECRET not in _session_text(home)

    with _mocked_auth(
        "Saved Jobs",
        auth_token="issued-token",
        candidate_id=9,
        candidate_name="Ada Lovelace",
    ) as (saved, _calls):
        assert saved.session_state["auth_token"] is None
        assert saved.session_state["nav"] == "Login"
        assert any("expired" in item.value.casefold() for item in saved.error)
