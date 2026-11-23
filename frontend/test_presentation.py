"""Checks that each existing page keeps its layout markers. API calls stay mocked."""

import sys
from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parent
if str(FRONTEND_DIR) not in sys.path:
    sys.path.insert(0, str(FRONTEND_DIR))

from test_home_profile_saved import _markdown, _mocked_app
from test_match_insights import SAMPLE_MATCHES


def test_public_pages_share_the_account_card():
    with _mocked_app("Login") as (login, calls):
        text = _markdown(login)
        assert "<p class='eyebrow page-eyebrow'>Account</p>" in text
        assert "<p class='section-label auth-card'>Sign in</p>" in text
        assert any(item.value == "Welcome back" for item in login.title)
        assert [button.label for button in login.button if button.label in {
            "Log in",
            "Create an account",
            "Set a password for an existing profile",
        }] == ["Log in", "Create an account", "Set a password for an existing profile"]
        assert calls == [("GET", "http://127.0.0.1:8001/", None)]

    with _mocked_app("Sign Up") as (signup, _calls):
        labels = [widget.label for widget in signup.text_input]
        assert labels[:4] == ["Name", "Email", "Password", "Confirm password"]
        assert "<p class='section-label auth-card'>Sign up</p>" in _markdown(signup)
        assert "8 to 128 characters" in _markdown(signup)

    with _mocked_app("Account setup") as (setup, _calls):
        text = _markdown(setup)
        assert "<p class='section-label auth-card'>Account setup</p>" in text
        assert "1. Enter the registered email." in text
        assert "The code expires in 10 minutes" in text
        assert any(item.value == "Set a password" for item in setup.title)
        assert any(button.label == "Back to login" for button in setup.button)

    with _mocked_app("Forgot password") as (forgot, _calls):
        text = _markdown(forgot)
        assert "<p class='section-label auth-card'>Forgot password</p>" in text
        assert "1. Enter the account email." in text
        assert "returns you to login" in text
        assert any(button.label == "Send OTP" for button in forgot.button)


def test_signed_in_pages_keep_their_cards():
    profile = {
        "id": 4,
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "education": "Mathematics",
        "skills": ["Python", "SQL"],
        "preferred_roles": ["Analyst"],
        "preferred_locations": ["London"],
        "years_experience": 3,
    }
    with _mocked_app(
        "Home",
        auth_token="test-token",
        candidate_id=4,
        candidate_name="Ada Lovelace",
        profile=profile,
    ) as (home, calls):
        text = _markdown(home)
        assert "<p class='eyebrow home-hero'>Welcome</p>" in text
        assert "<p class='section-label kpi-card'>Saved jobs</p>" in text
        assert "AI Job Matching" in text
        assert any(url.endswith("/matches") for _, url, _ in calls)
        assert any(button.label == "Discover Jobs" for button in home.button)

    with _mocked_app(
        "Discover Jobs",
        auth_token="test-token",
        candidate_id=4,
        candidate_name="Ada Lovelace",
        profile=profile,
    ) as (discover, calls):
        text = _markdown(discover)
        assert "<p class='section-label discover-empty'>No jobs are stored yet</p>" in text
        assert "Resume" not in text
        assert any(url.split("?")[0].endswith("/jobs/") for _, url, _ in calls)

    with _mocked_app(
        "Match Insights",
        auth_token="test-token",
        candidate_id=4,
        candidate_name="Ada Lovelace",
        matches=None,
    ) as (waiting, _calls):
        assert "<p class='section-label match-empty'>No ranking yet</p>" in _markdown(waiting)
        assert any(button.label == "Find matches" for button in waiting.button)

    with _mocked_app(
        "Match Insights",
        auth_token="test-token",
        candidate_id=1,
        candidate_name="Sample Candidate",
        matches=SAMPLE_MATCHES,
    ) as (ranked, _calls):
        text = _markdown(ranked)
        assert "<p class='section-label match-controls'>Choose a job</p>" in text
        assert text.count("<h3 class='match-title match-card'>") == 1

    with _mocked_app(
        "Saved Jobs",
        auth_token="test-token",
        candidate_id=4,
        candidate_name="Ada Lovelace",
        saved_jobs=[],
    ) as (empty_saved, calls):
        text = _markdown(empty_saved)
        assert "<p class='section-label saved-empty'>Nothing saved yet</p>" in text
        assert "Unsave" not in text
        assert not any(method == "POST" for method, _, _ in calls)
