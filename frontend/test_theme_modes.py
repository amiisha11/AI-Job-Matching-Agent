"""Light and dark theme configuration. No network calls and no secrets."""

import sys
import tomllib
from pathlib import Path

from streamlit import config as st_config

FRONTEND_DIR = Path(__file__).resolve().parent
ROOT = FRONTEND_DIR.parent
if str(FRONTEND_DIR) not in sys.path:
    sys.path.insert(0, str(FRONTEND_DIR))

from theme import CSS, _THEME_SYNC

CONFIG_PATH = ROOT / ".streamlit" / "config.toml"
LIGHT_PRIMARY = "#397D68"
LIGHT_BACKGROUND = "#F3F6F3"
LIGHT_SURFACE = "#FFFFFF"
LIGHT_TEXT = "#202923"

PAGE_SOURCES = {
    "frontend/pages.py": (
        "home-dashboard",
        "profile-dashboard",
        "discover-page",
        "saved-page",
        "prep-notes",
        "Match Insights",
    ),
    "frontend/auth_pages.py": (
        "Sign in",
        "Sign up",
        "Account setup",
        "Forgot password",
        "Change password",
        "auth-card",
    ),
    "frontend/resume_centre.py": ("resume-page",),
    "frontend/app.py": (
        "inject_theme()",
        "page_home",
        "page_profile",
        "page_discover",
        "page_matches",
        "page_saved",
        "page_resume",
        "page_login",
        "page_signup",
        "page_setup",
        "page_forgot",
    ),
}
STYLED_MARKERS = (
    "home-dashboard",
    "profile-dashboard",
    "discover-page",
    "prep-next",
    "auth-card",
    "resume-page",
    "match-card",
    "saved-summary-line",
    "saved-card-body",
)


def _theme_config():
    return tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))["theme"]


def test_streamlit_accepts_the_dual_theme_config():
    theme = _theme_config()
    assert "base" not in theme
    assert theme["font"] == "sans serif"
    assert set(theme) >= {"font", "light", "dark"}
    assert "sidebar" in theme["light"]
    assert "sidebar" in theme["dark"]

    assert st_config.get_option("theme.font") == "sans serif"
    assert st_config.get_option("theme.light.primaryColor") == LIGHT_PRIMARY
    assert st_config.get_option("theme.dark.backgroundColor") == "#090B0E"
    assert st_config.get_option("theme.light.sidebar.backgroundColor") == "#18211E"
    assert st_config.get_option("theme.dark.sidebar.textColor") == "#F2F5F2"
    assert st_config.get_option("client.toolbarMode") == "auto"


def test_light_theme_keeps_the_existing_colours():
    light = _theme_config()["light"]
    assert light["primaryColor"] == LIGHT_PRIMARY
    assert light["backgroundColor"] == LIGHT_BACKGROUND
    assert light["secondaryBackgroundColor"] == LIGHT_SURFACE
    assert light["textColor"] == LIGHT_TEXT
    assert LIGHT_BACKGROUND in CSS
    assert LIGHT_PRIMARY in CSS
    assert LIGHT_SURFACE in CSS
    assert LIGHT_TEXT in CSS
    assert "#20B8A0" in CSS
    assert "#243656" not in CSS
    assert "#6D62C8" not in CSS
    assert "min-width: 116px" in CSS
    assert "min-height: 23px" in CSS


def test_dark_tokens_override_the_same_semantic_names():
    dark = CSS.split('html[data-theme="dark"]', 1)[1]
    for token in (
        "--app-bg",
        "--sidebar-bg",
        "--surface-primary",
        "--surface-secondary",
        "--surface-elevated",
        "--text-primary",
        "--text-secondary",
        "--text-muted",
        "--brand",
        "--brand-secondary",
        "--border",
        "--input-bg",
        "--success",
        "--warning",
        "--error",
        "--chart-bg",
        "--chart-text",
    ):
        assert token in CSS
        assert token in dark
    assert "--st-primary-color" not in CSS
    assert "colorScheme" in _THEME_SYNC
    assert "localStorage" not in _THEME_SYNC
    assert "#090B0E" in dark
    assert "#F2F5F2" in dark
    assert "#75A995" in dark


def test_charts_follow_the_active_theme():
    theme = _theme_config()
    for mode in ("light", "dark"):
        assert len(theme[mode]["chartCategoricalColors"]) >= 2
        assert len(theme[mode]["chartSequentialColors"]) == 10
        assert len(theme[mode]["chartDivergingColors"]) == 10
        assert len(set(theme[mode]["chartCategoricalColors"])) == len(
            theme[mode]["chartCategoricalColors"]
        )
    assert "background: var(--chart-bg)" in CSS
    assert "color: var(--chart-text)" in CSS
    assert theme["light"]["chartCategoricalColors"] != theme["dark"]["chartCategoricalColors"]


def test_shared_styles_and_every_screen_use_the_theme():
    for selector in (
        '[data-testid="stSidebar"] .stButton > button[kind="primary"]',
        ".stButton > button[kind=\"primary\"]",
        ".score-plot",
        ".adzuna-credit",
        "background: var(--surface)",
        "background: var(--input-bg)",
    ):
        assert selector in CSS
    for marker in STYLED_MARKERS:
        assert marker in CSS
    for relative, markers in PAGE_SOURCES.items():
        source = (ROOT / relative).read_text(encoding="utf-8")
        for marker in markers:
            assert marker in source
