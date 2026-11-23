"""Shared styling for the Streamlit screens.

Light values stay on :root. Dark values override the same semantic tokens
when the native Streamlit theme sets color-scheme: dark on .stApp.
Streamlit 1.67 does not expose --st-primary-color and the other theme
variables on the page, so those names are not used as colour sources.
"""

import streamlit as st

CSS = """
<style>
:root {
    --app-bg: #F3F6F3;
    --sidebar-bg: #18211E;
    --surface-primary: #FFFFFF;
    --surface-secondary: #F8FAF8;
    --surface-elevated: #F8FAF8;
    --surface-soft-color: #F8FAF8;
    --text-primary: #202923;
    --text-secondary: #5F6D65;
    --text-muted: #85928B;
    --brand: #397D68;
    --brand-hover: #2F6B59;
    --brand-text: #397D68;
    --brand-secondary: #E6F0EB;
    --brand-secondary-strong: #C9D9D1;
    --border: #DCE5DF;
    --input-bg: #FFFFFF;
    --success: #2F7D4A;
    --warning: #A16207;
    --error: #B42318;
    --chart-bg: #FFFFFF;
    --chart-text: #202923;
    --fill-strong: #18211E;
    --badge-bg: #FFFFFF;
    --badge-ink: #202923;
    --on-accent: #FFFFFF;
    --navy: var(--text-secondary);
    --sidebar: var(--sidebar-bg);
    --lavender: var(--brand-secondary);
    --lavender-strong: var(--brand-secondary-strong);
    --accent: var(--brand);
    --accent-hover: var(--brand-hover);
    --accent-text: var(--brand-text);
    --white: #FFFFFF;
    --ink: var(--text-primary);
    --muted: var(--text-muted);
    --line: var(--border);
    --page: var(--app-bg);
    --surface: var(--surface-primary);
    --surface-muted: var(--surface-secondary);
    --surface-soft: var(--surface-soft-color);
    --ok: var(--success);
    --warn: var(--warning);
    --danger: var(--error);
    --score-high: #20B8A0;
    --score-mid: #397D68;
    --score-fair: #8FA89C;
    --score-low: #C5D1CB;
    --sidebar-text: #F2F5F2;
    --sidebar-muted: #B5C0BA;
    --sidebar-active: rgba(117, 169, 149, 0.22);
    --sidebar-hover: rgba(117, 169, 149, 0.1);
    --shadow: 0 8px 22px rgba(24, 33, 30, 0.06);
    --shadow-soft: 0 4px 12px rgba(24, 33, 30, 0.04);
    --focus-ring: 0 0 0 3px rgba(57, 125, 104, 0.22);
    --chip-line: #C5D1CB;
    --sidebar-active-hover: rgba(117, 169, 149, 0.32);
    --sidebar-panel: rgba(255, 255, 255, 0.06);
    --sidebar-panel-line: rgba(197, 209, 203, 0.28);
    --status-ok-bg: #C9F2D6;
    --status-down-bg: #F0C9C4;
    --step-bg: #F8FAF8;
    --step-current-bg: #E6F0EB;
    --step-current-ink: #18211E;
    --completion-open: #F8FAF8;
    --completion-line: #DCE5DF;
    --completion-ok-bg: #E4F3EA;
    --resume-found-bg: #E6F0EB;
    --control-line: #DCE5DF;
    --home-card: var(--surface-elevated);
    --radius-card: 16px;
    --radius-control: 12px;
    --radius-button: 10px;
    --radius-inner: 14px;
    --space-2: 0.55rem;
    --space-3: 0.85rem;
    --space-4: 1.15rem;
    --space-5: 1.5rem;
    --text-xs: 0.78rem;
    --text-sm: 0.92rem;
    --text-lg: 1.28rem;
    --text-xl: 1.7rem;
}

html[data-theme="dark"] {
    --app-bg: #090B0E;
    --sidebar-bg: #090B0E;
    --surface-primary: #171B20;
    --surface-secondary: #171B20;
    --surface-elevated: #202630;
    --surface-soft-color: #202630;
    --text-primary: #F2F5F2;
    --text-secondary: #B5C0BA;
    --text-muted: #87928C;
    --brand: #75A995;
    --brand-hover: #8DBBA9;
    --brand-text: #75A995;
    --brand-secondary: #203A34;
    --brand-secondary-strong: #2E4A42;
    --border: #303740;
    --input-bg: #202630;
    --success: #8ED4A8;
    --warning: #E6C27A;
    --error: #F0B4AE;
    --chart-bg: #171B20;
    --chart-text: #F2F5F2;
    --fill-strong: #202630;
    --badge-bg: #202630;
    --badge-ink: #F2F5F2;
    --on-accent: #07130F;
    --score-mid: #75A995;
    --score-fair: #8DBBA9;
    --score-low: #5F6D65;
    --chip-line: #303740;
    --shadow: 0 8px 22px rgba(0, 0, 0, 0.32);
    --shadow-soft: 0 4px 12px rgba(0, 0, 0, 0.24);
    --focus-ring: 0 0 0 3px rgba(117, 169, 149, 0.35);
    --status-ok-bg: #1F6B45;
    --status-down-bg: #8C3A34;
    --step-bg: #171B20;
    --step-current-bg: #203A34;
    --step-current-ink: #F2F5F2;
    --completion-open: #171B20;
    --completion-line: #303740;
    --completion-ok-bg: #1A3D2C;
    --resume-found-bg: #203A34;
    --control-line: #303740;
    --sidebar-active: rgba(117, 169, 149, 0.18);
    --sidebar-hover: rgba(117, 169, 149, 0.08);
    --sidebar-active-hover: rgba(117, 169, 149, 0.28);
    --sidebar-panel: rgba(255, 255, 255, 0.05);
    --sidebar-panel-line: rgba(48, 55, 64, 0.9);
}

html, body, .stApp {
    background: var(--page);
    color: var(--ink);
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 16px;
}

.main .block-container {
    max-width: 1120px;
    padding-top: var(--space-5);
    padding-bottom: 2.5rem;
    padding-left: var(--space-5);
    padding-right: var(--space-5);
}

.main [data-testid="stVerticalBlock"] {
    gap: var(--space-4);
}

[data-testid="stHorizontalBlock"] {
    gap: var(--space-4);
}

h1 {
    color: var(--ink);
    font-size: var(--text-xl);
    font-weight: 650;
    letter-spacing: -0.03em;
    line-height: 1.15;
    margin-bottom: 0.15rem;
}

h2, h3 {
    color: var(--ink);
    letter-spacing: -0.02em;
}

.page-subtitle {
    margin: 0.2rem 0 var(--space-4) 0;
    color: var(--muted);
    font-size: 1.02rem;
    line-height: 1.55;
}

.section-label {
    margin: 0 0 0.55rem 0;
    color: var(--muted);
    font-size: 0.78rem;
    font-weight: 650;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

.page-eyebrow {
    margin-bottom: 0.35rem;
}

.eyebrow {
    margin: 0 0 0.35rem 0;
    color: var(--accent-text);
    font-size: 0.78rem;
    font-weight: 650;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

.step-card,
.hero-copy,
.note {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 16px;
    box-shadow: var(--shadow);
}

.step-card {
    padding: 1.5rem 1.4rem 1.35rem 1.4rem;
    min-height: 0;
    border-radius: var(--radius-card);
    box-shadow: var(--shadow);
}

.step-card h3 {
    margin: 0 0 0.45rem 0;
    font-size: 1.12rem;
}

.step-card p,
.hero-copy p {
    margin: 0;
    color: var(--muted);
    line-height: 1.55;
}

.hero-copy {
    padding: 1.5rem 1.5rem;
}

.hero-title {
    margin: 0.15rem 0 0.55rem 0;
    color: var(--ink);
    font-size: 1.65rem;
    font-weight: 680;
    letter-spacing: -0.03em;
    line-height: 1.2;
}

.hero-lead,
.form-hint,
.detail-line,
.saved-date,
.auth-switch {
    margin: 0;
    color: var(--muted);
    line-height: 1.6;
}

.form-hint {
    margin-bottom: 0.85rem;
}

.auth-switch {
    margin: 1.15rem 0 0.15rem 0;
    font-size: 0.92rem;
}

.detail-line {
    margin-top: 0.35rem;
    color: var(--ink);
}

.saved-date {
    margin: 0.45rem 0 0.15rem 0;
    font-size: 0.92rem;
}

.status-line {
    margin: 0.85rem 0 0 0;
    color: var(--muted);
    font-size: 0.92rem;
}

[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--surface);
    border: 1px solid var(--line) !important;
    border-radius: var(--radius-card) !important;
    box-shadow: var(--shadow);
}

[data-testid="stVerticalBlockBorderWrapper"] > div {
    padding: 1.15rem 1.2rem 1.05rem 1.2rem;
}

[data-testid="stVerticalBlock"][data-test-scroll-behavior] {
    background: var(--surface);
    border: 1px solid var(--line) !important;
    border-radius: var(--radius-card) !important;
    box-shadow: var(--shadow);
    padding: 1.15rem 1.2rem 1.05rem 1.2rem;
}

[data-testid="stVerticalBlock"][data-test-scroll-behavior]:has(.kpi-card) {
    height: auto;
    padding: 1rem 1.05rem 0.95rem 1.05rem;
}

[data-testid="stVerticalBlock"][data-test-scroll-behavior]:has(.discover-card) {
    display: flex;
    flex-direction: column;
    height: 100%;
    padding: 1rem 1rem 0.9rem 1rem;
}

[data-testid="stMetric"] {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--radius-card);
    padding: 1rem 1.05rem 0.9rem 1.05rem;
    box-shadow: var(--shadow);
}

[data-testid="stMetricValue"] {
    color: var(--navy);
    font-weight: 700;
    letter-spacing: -0.03em;
}

[data-testid="stMetricLabel"] {
    color: var(--muted);
}

[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
[data-testid="stMultiSelect"] div[data-baseweb="select"] > div {
    background: var(--input-bg);
    color: var(--ink);
    border-color: var(--lavender-strong) !important;
    border-radius: 12px !important;
    min-height: 2.75rem;
}

[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus,
[data-testid="stSelectbox"] div[data-baseweb="select"] > div:focus-within,
[data-testid="stMultiSelect"] div[data-baseweb="select"] > div:focus-within {
    border-color: var(--accent-text) !important;
    box-shadow: var(--focus-ring);
}

[data-testid="stWidgetLabel"] p {
    color: var(--navy);
    font-weight: 600;
}

[data-testid="stForm"] {
    border: none;
    padding: 0;
    background: transparent;
}

[data-testid="stForm"] [data-testid="stVerticalBlock"] {
    gap: 1rem;
}

.stButton > button,
.stFormSubmitButton > button {
    border-radius: var(--radius-button);
    min-height: 2.6rem;
    padding: 0.4rem 1rem;
    font-weight: 600;
    transition: background 0.15s ease, border-color 0.15s ease;
}

.stButton > button {
    background: var(--surface);
    color: var(--ink);
    border: 1px solid var(--lavender-strong);
}

.stButton > button:hover {
    border-color: var(--accent-text);
    color: var(--ink);
    background: var(--page);
}

.stButton > button[kind="primary"],
.stFormSubmitButton > button {
    background: var(--accent);
    color: var(--on-accent);
    border: 1px solid var(--accent);
}

.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button:hover {
    background: var(--accent-hover);
    border-color: var(--accent-hover);
    color: var(--on-accent);
}

.stFormSubmitButton {
    margin-top: 0.35rem;
}

.stFormSubmitButton > button {
    min-width: 11rem;
}

[data-testid="stAlert"] {
    border-radius: var(--radius-inner) !important;
    border: 1px solid var(--line) !important;
}

.note {
    padding: 0.95rem 1.05rem;
    margin: 0.35rem 0 0.2rem 0;
    color: var(--ink);
    line-height: 1.6;
    box-shadow: none;
    background: var(--surface-muted);
}

.chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    margin: 0.15rem 0 0.35rem 0;
    max-width: 100%;
}

.chip {
    display: inline-block;
    margin: 0;
    max-width: 100%;
    padding: 0.32rem 0.8rem;
    border-radius: 999px;
    font-size: 0.92rem;
    line-height: 1.4;
    white-space: normal;
    overflow-wrap: anywhere;
}

.chip-exact {
    background: var(--fill-strong);
    color: var(--white);
}

.chip-semantic {
    background: var(--lavender);
    color: var(--navy);
}

.chip-missing {
    background: var(--surface);
    color: var(--navy);
    border: 1px solid var(--chip-line);
}

[data-testid="stSidebar"] {
    background: var(--sidebar);
    border-right: none;
}

[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] div {
    color: var(--sidebar-text);
}

[data-testid="stSidebarUserContent"] {
    padding-top: 0.4rem;
}

[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
    gap: 0.3rem;
    min-height: calc(100vh - 7.5rem);
}

[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(.sidebar-session) {
    margin-top: auto;
}

.sidebar-brand {
    display: flex;
    gap: 0.8rem;
    align-items: center;
    margin: 0.2rem 0 1.3rem 0;
}

.sidebar-mark {
    width: 2.4rem;
    height: 2.4rem;
    border-radius: 12px;
    background: var(--lavender);
    color: var(--navy) !important;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    letter-spacing: 0;
}

.sidebar-title {
    margin: 0;
    font-size: 1.02rem;
    font-weight: 700;
}

.sidebar-tag,
.sidebar-meta {
    margin: 0.15rem 0 0 0;
    color: var(--sidebar-muted) !important;
    font-size: 0.84rem;
    line-height: 1.4;
}

[data-testid="stSidebar"] .stButton > button {
    display: flex;
    align-items: center;
    justify-content: flex-start;
    gap: 0.65rem;
    width: 100%;
    min-height: 2.45rem;
    margin: 0;
    padding: 0.45rem 0.8rem;
    text-align: left;
    background: transparent;
    color: var(--sidebar-text) !important;
    border: 1px solid transparent;
    border-radius: var(--radius-control);
}

[data-testid="stSidebar"] .stButton > button p,
[data-testid="stSidebar"] .stButton > button span {
    color: inherit !important;
}

[data-testid="stSidebar"] .stButton > button:hover {
    background: var(--sidebar-hover);
    color: var(--sidebar-text) !important;
    border-color: transparent;
}

[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: var(--sidebar-active);
    color: var(--white) !important;
    border-color: transparent;
    box-shadow: inset 3px 0 0 var(--accent);
    font-weight: 700;
}

[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
    background: var(--sidebar-active-hover);
    color: var(--white) !important;
    border-color: transparent;
}

.status-dot {
    display: inline-block;
    width: 0.45rem;
    height: 0.45rem;
    margin-right: 0.4rem;
    border-radius: 999px;
    vertical-align: 0.05rem;
}

.status-ok {
    background: var(--status-ok-bg);
}

.status-down {
    background: var(--status-down-bg);
}

.sidebar-session {
    margin-top: auto;
    background: var(--sidebar-panel);
    border: 1px solid var(--sidebar-panel-line);
    border-radius: var(--radius-inner);
    padding: 0.95rem 1rem 0.8rem 1rem;
}

.sidebar-kicker {
    margin: 0 0 0.3rem 0;
    color: var(--chip-line) !important;
    font-size: 0.72rem;
    font-weight: 650;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

.sidebar-name {
    margin: 0;
    font-weight: 650;
}

[data-testid="stVerticalBlockBorderWrapper"]:has(.match-card) {
    background: var(--surface);
    border: 1px solid var(--line) !important;
    border-radius: var(--radius-card) !important;
    box-shadow: var(--shadow);
    margin-bottom: 1.15rem;
}

[data-testid="stVerticalBlockBorderWrapper"]:has(.match-card) > div {
    padding: 1.5rem 1.5rem 1.35rem 1.5rem;
}

.match-title {
    margin: 0 0 0.35rem 0;
    color: var(--ink);
    font-size: 1.45rem;
    font-weight: 680;
    letter-spacing: -0.03em;
    line-height: 1.2;
    overflow-wrap: anywhere;
}

.match-company {
    margin: 0;
    color: var(--ink);
    font-size: 1rem;
    font-weight: 600;
    overflow-wrap: anywhere;
}

.match-location {
    margin: 0.2rem 0 0.15rem 0;
    color: var(--muted);
    font-size: 0.95rem;
    overflow-wrap: anywhere;
}

[data-testid="stColumn"]:has(.score-label) {
    background: var(--surface-muted);
    border: 1px solid var(--line);
    border-radius: var(--radius-inner);
    padding: 0.85rem 0.9rem 0.7rem 0.9rem;
}

.score-label {
    margin: 0;
    color: var(--muted);
    font-size: 0.72rem;
    font-weight: 650;
    letter-spacing: 0.07em;
    text-transform: uppercase;
}

.score-value {
    margin: 0.28rem 0 0.45rem 0;
    color: var(--navy);
    font-size: 1.28rem;
    font-weight: 700;
    letter-spacing: -0.03em;
    line-height: 1.1;
}

.score-value span {
    color: var(--muted);
    font-size: 0.82rem;
    font-weight: 600;
    letter-spacing: 0;
}

[data-testid="stColumn"]:has(.score-label) [data-testid="stProgress"] > div:first-child {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
}

[data-testid="stColumn"]:has(.score-label) [data-testid="stProgressBarTrack"] {
    height: 10px !important;
    border-radius: 999px !important;
    background: var(--lavender) !important;
    overflow: hidden;
}

[data-testid="stColumn"]:has(.score-label) [data-testid="stProgressBarTrack"] > div {
    background: var(--accent) !important;
}

.skill-heading {
    margin: 0.7rem 0 0.35rem 0;
    color: var(--navy);
    font-size: 0.95rem;
    font-weight: 650;
}

.insight-panel {
    background: var(--surface-soft);
    border: 1px solid var(--line);
    border-radius: var(--radius-inner);
    padding: 1rem 1.1rem;
    margin: 0.15rem 0 0.85rem 0;
    color: var(--ink);
    line-height: 1.65;
}

[data-testid="stVerticalBlockBorderWrapper"]:has(.match-card) .stButton > button {
    min-width: 0;
    width: 100%;
    white-space: normal;
}

.main:has(.match-page) .match-title.match-card {
    margin: 0 0 0.2rem 0;
    font-size: 1.2rem;
    line-height: 1.3;
    overflow-wrap: anywhere;
}

.main:has(.match-page) .score-hero {
    color: var(--accent-text);
    font-size: 2.35rem;
    line-height: 1;
}

.main:has(.match-page) .score-row {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 0.75rem;
    margin: 0.45rem 0 0 0;
}

.main:has(.match-page) .score-row .score-value {
    margin: 0;
    font-size: 0.92rem;
}

.main:has(.match-page) [data-testid="stProgress"] > div:first-child {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
}

.main:has(.match-page) [data-testid="stProgressBarTrack"] {
    height: 8px !important;
    border-radius: 999px !important;
    background: var(--lavender) !important;
    overflow: hidden;
}

.main:has(.match-page) [data-testid="stProgressBarTrack"] > div {
    background: var(--accent) !important;
}

.main:has(.match-page) [data-testid="stColumn"]:has(.skill-heading) {
    min-width: 0 !important;
    background: var(--surface-muted);
    border: 1px solid var(--line);
    border-radius: var(--radius-inner);
    padding: 0.7rem 0.75rem 0.45rem 0.75rem;
}

.main:has(.match-page) .skill-pair {
    margin: 0 0 0.45rem 0;
}

.main:has(.match-page) .skill-pair .detail-line span {
    display: block;
    color: var(--muted);
    font-size: 0.72rem;
    font-weight: 650;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}

.main:has(.match-page) .skill-pair-phrase {
    margin: 0.15rem 0 0 0;
    color: var(--muted);
    font-size: 0.78rem;
    line-height: 1.35;
}

.main:has(.match-page) .match-explanation {
    max-width: 68ch;
    margin-top: 0.25rem;
    font-size: 0.95rem;
    line-height: 1.6;
}

.main:has(.match-page) .match-meta {
    margin-top: 0.45rem;
}

.main:has(.match-page) .detail-line,
.main:has(.match-page) .form-hint,
.main:has(.match-page) .match-company,
.main:has(.match-page) .match-location {
    overflow-wrap: anywhere;
}

.main:has(.match-page) .chip {
    max-width: 100%;
    white-space: normal;
    overflow-wrap: anywhere;
}

.main:has(.match-page) [data-testid="stHorizontalBlock"]:has(.stButton) {
    flex-wrap: wrap;
}

.main:has(.match-page) [data-testid="stHorizontalBlock"]:has(.stButton) > [data-testid="stColumn"] {
    flex: 1 1 8.5rem !important;
    min-width: 0 !important;
    width: auto !important;
}

[data-testid="stVerticalBlockBorderWrapper"]:has(.home-hero),
[data-testid="stVerticalBlockBorderWrapper"]:has(.home-profile),
[data-testid="stVerticalBlockBorderWrapper"]:has(.home-empty),
[data-testid="stVerticalBlockBorderWrapper"]:has(.profile-card),
[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-card),
[data-testid="stVerticalBlockBorderWrapper"]:has(.profile-summary),
[data-testid="stVerticalBlockBorderWrapper"]:has(.saved-card),
[data-testid="stVerticalBlockBorderWrapper"]:has(.saved-controls),
[data-testid="stVerticalBlockBorderWrapper"]:has(.saved-empty),
[data-testid="stVerticalBlockBorderWrapper"]:has(.match-controls),
[data-testid="stVerticalBlockBorderWrapper"]:has(.match-empty),
[data-testid="stVerticalBlockBorderWrapper"]:has(.discover-card),
[data-testid="stVerticalBlockBorderWrapper"]:has(.prep-plan),
[data-testid="stVerticalBlockBorderWrapper"]:has(.discover-empty),
[data-testid="stVerticalBlockBorderWrapper"]:has(.home-actions),
[data-testid="stVerticalBlockBorderWrapper"]:has(.home-hero),
[data-testid="stVerticalBlockBorderWrapper"]:has(.kpi-card),
[data-testid="stVerticalBlockBorderWrapper"]:has(.chart-card),
[data-testid="stVerticalBlockBorderWrapper"]:has(.home-recent),
[data-testid="stVerticalBlockBorderWrapper"]:has(.home-saved),
[data-testid="stVerticalBlockBorderWrapper"]:has(.profile-overview),
[data-testid="stVerticalBlockBorderWrapper"]:has(.profile-info),
[data-testid="stVerticalBlockBorderWrapper"]:has(.profile-skills),
[data-testid="stVerticalBlockBorderWrapper"]:has(.profile-completion),
[data-testid="stVerticalBlockBorderWrapper"]:has(.gate-card) {
    background: var(--surface);
    border: 1px solid var(--line) !important;
    border-radius: var(--radius-card) !important;
    box-shadow: var(--shadow);
    margin-bottom: 1.15rem;
}

[data-testid="stVerticalBlockBorderWrapper"]:has(.home-hero) > div,
[data-testid="stVerticalBlockBorderWrapper"]:has(.home-profile) > div,
[data-testid="stVerticalBlockBorderWrapper"]:has(.home-empty) > div,
[data-testid="stVerticalBlockBorderWrapper"]:has(.profile-card) > div,
[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-card) > div,
[data-testid="stVerticalBlockBorderWrapper"]:has(.profile-summary) > div,
[data-testid="stVerticalBlockBorderWrapper"]:has(.saved-card) > div,
[data-testid="stVerticalBlockBorderWrapper"]:has(.saved-controls) > div,
[data-testid="stVerticalBlockBorderWrapper"]:has(.saved-empty) > div,
[data-testid="stVerticalBlockBorderWrapper"]:has(.match-controls) > div,
[data-testid="stVerticalBlockBorderWrapper"]:has(.match-empty) > div,
[data-testid="stVerticalBlockBorderWrapper"]:has(.discover-card) > div,
[data-testid="stVerticalBlockBorderWrapper"]:has(.prep-plan) > div,
[data-testid="stVerticalBlockBorderWrapper"]:has(.discover-empty) > div,
[data-testid="stVerticalBlockBorderWrapper"]:has(.home-actions) > div,
[data-testid="stVerticalBlockBorderWrapper"]:has(.kpi-card) > div,
[data-testid="stVerticalBlockBorderWrapper"]:has(.chart-card) > div,
[data-testid="stVerticalBlockBorderWrapper"]:has(.home-recent) > div,
[data-testid="stVerticalBlockBorderWrapper"]:has(.home-saved) > div,
[data-testid="stVerticalBlockBorderWrapper"]:has(.profile-overview) > div,
[data-testid="stVerticalBlockBorderWrapper"]:has(.profile-info) > div,
[data-testid="stVerticalBlockBorderWrapper"]:has(.profile-skills) > div,
[data-testid="stVerticalBlockBorderWrapper"]:has(.profile-completion) > div,
[data-testid="stVerticalBlockBorderWrapper"]:has(.gate-card) > div {
    padding: 1.5rem 1.5rem 1.35rem 1.5rem;
}

[data-testid="stVerticalBlockBorderWrapper"]:has(.profile-card) [data-testid="stVerticalBlock"] {
    gap: 0.95rem;
}

[data-testid="stForm"]:has(.profile-card) {
    margin-bottom: 0.4rem;
}

[data-testid="stForm"]:has(.profile-card) .stFormSubmitButton {
    margin-top: 0.85rem;
}

.main:has(.profile-builder) [data-baseweb="tag"] {
    background: var(--fill-strong) !important;
    border-radius: 999px !important;
    border: none !important;
}

.main:has(.profile-builder) [data-baseweb="tag"] span {
    color: var(--white) !important;
}

.main:has(.auth-card) .block-container {
    max-width: 640px;
}

.main:has(.auth-card) .stButton > button,
[data-testid="stVerticalBlockBorderWrapper"]:has(.password-form) .stButton > button {
    width: 100%;
    white-space: normal;
}

.main:has(.auth-card) [data-testid="stTextInput"] input {
    max-width: 100%;
}

.auth-brand {
    display: flex;
    gap: 0.7rem;
    align-items: center;
    margin-bottom: 0.9rem;
    color: var(--navy);
    font-weight: 700;
}

.profile-context {
    margin-bottom: 0.2rem;
}

.kpi-value {
    margin: 0.15rem 0 0.35rem 0;
    color: var(--navy);
    font-size: 1.85rem;
    font-weight: 700;
    letter-spacing: -0.03em;
    line-height: 1.1;
}

.home-note {
    margin: 0.15rem 0 0.85rem 0;
    color: var(--muted);
    font-size: 0.92rem;
    line-height: 1.45;
}

.home-note-soft {
    margin-top: 0.15rem;
    padding: 0.55rem 0.85rem;
    border-radius: 12px;
    background: var(--surface-soft);
}

.kpi-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 2rem;
    height: 2rem;
    margin-bottom: 0.75rem;
    border-radius: 10px;
    background: var(--lavender);
    color: var(--navy);
}

.kpi-icon svg {
    width: 1.05rem;
    height: 1.05rem;
    fill: none;
    stroke: currentColor;
    stroke-width: 1.7;
    stroke-linecap: round;
    stroke-linejoin: round;
}

.main:has(.home-dashboard) [data-testid="stVerticalBlockBorderWrapper"]:has(.kpi-card) {
    height: auto;
    overflow: visible;
}

.main:has(.home-dashboard) [data-testid="stVerticalBlockBorderWrapper"]:has(.kpi-card) > div {
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    height: auto;
    box-sizing: border-box;
    padding: 1rem 1.05rem 0.95rem 1.05rem;
}

.main:has(.home-dashboard) .kpi-card,
.main:has(.home-dashboard) [data-testid="stVerticalBlockBorderWrapper"]:has(.kpi-card) .hero-lead {
    overflow-wrap: anywhere;
}

.main:has(.home-dashboard) [data-testid="stVerticalBlockBorderWrapper"]:has(.kpi-card) .hero-lead {
    font-size: 0.86rem;
    line-height: 1.4;
}

.main:has(.discover-page) [data-testid="stVerticalBlock"]:has(.discover-grid):not(:has([data-testid="stVerticalBlock"] .discover-grid)) {
    display: grid !important;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.9rem 1rem;
    align-items: stretch;
}

.main:has(.saved-page) [data-testid="stVerticalBlock"]:has(.discover-grid):not(:has([data-testid="stVerticalBlock"] .discover-grid)) {
    grid-template-columns: repeat(3, minmax(0, 1fr));
}

.main:has(.discover-page) [data-testid="stVerticalBlock"]:has(.discover-grid):not(:has([data-testid="stVerticalBlock"] .discover-grid)) > [data-testid="element-container"]:has(.discover-grid),
.main:has(.discover-page) [data-testid="stVerticalBlock"]:has(.discover-grid):not(:has([data-testid="stVerticalBlock"] .discover-grid)) > div:has(.discover-grid) {
    display: none;
}

.main:has(.discover-page) [data-testid="stVerticalBlock"]:has(.discover-grid):not(:has([data-testid="stVerticalBlock"] .discover-grid)) > [data-testid="element-container"]:has(.discover-card),
.main:has(.discover-page) [data-testid="stVerticalBlock"]:has(.discover-grid):not(:has([data-testid="stVerticalBlock"] .discover-grid)) [data-testid="stHorizontalBlock"]:has(.discover-card) {
    display: contents !important;
}

.main:has(.discover-page) [data-testid="stVerticalBlock"]:has(.discover-grid) [data-testid="stColumn"]:has(.discover-card) {
    width: auto !important;
    min-width: 0 !important;
    max-width: none !important;
    flex: none !important;
    box-sizing: border-box;
}

.main:has(.discover-page) [data-testid="stHorizontalBlock"]:has(.discover-card) > [data-testid="stColumn"]:not(:has(.discover-card)) {
    display: none !important;
}

.main:has(.discover-page) [data-testid="stVerticalBlockBorderWrapper"]:has(.discover-card) {
    height: 100%;
    overflow: visible;
}

.main:has(.discover-page):not(:has(.saved-page)) [data-testid="stVerticalBlockBorderWrapper"]:has(.discover-card) {
    box-shadow: var(--shadow-soft);
}

.main:has(.discover-page) [data-testid="stVerticalBlockBorderWrapper"]:has(.discover-card) > div {
    display: flex;
    flex-direction: column;
    height: 100%;
    box-sizing: border-box;
    padding: 1rem 1rem 0.9rem 1rem;
}

.main:has(.discover-page):not(:has(.saved-page)) [data-testid="stVerticalBlockBorderWrapper"]:has(.discover-card) > div {
    padding: 0.8rem 0.85rem 0.7rem 0.85rem;
}

.discover-card {
    overflow-wrap: break-word;
    word-break: normal;
    margin: 0 0 0.15rem 0;
    font-size: 1.02rem;
    line-height: 1.3;
}

.main:has(.discover-page):not(:has(.saved-page)) .match-title.discover-card {
    margin: 0 0 0.1rem 0;
    color: var(--ink);
    font-size: 1.05rem;
    font-weight: 680;
    line-height: 1.3;
}

.discover-badge {
    margin: 0 0 0.4rem 0;
}

.discover-badge .adzuna-credit {
    min-width: 0;
    min-height: 1.25rem;
    margin: 0;
    padding: 0.12rem 0.5rem;
    border: 1px solid var(--chip-line);
    border-radius: 999px;
    background: var(--lavender);
    color: var(--navy);
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.01em;
}

.main:has(.discover-page) [data-testid="stElementContainer"]:has(.discover-actions),
.main:has(.discover-page) [data-testid="element-container"]:has(.discover-actions) {
    margin-top: auto;
}

.discover-actions .adzuna-apply {
    margin: 0 0 0.3rem 0;
}

.main:has(.discover-page) .detail-line,
.main:has(.discover-page) .discover-score,
.main:has(.discover-page) .discover-more {
    margin: 0.12rem 0;
    color: var(--muted);
    font-size: 0.84rem;
    line-height: 1.35;
}

.main:has(.discover-page) .score-value.discover-score {
    color: var(--accent-text);
    font-weight: 700;
}

.discover-sources {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.35rem 0.55rem;
    margin-top: 0.45rem;
}

.main:has(.discover-page) .chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
}

.main:has(.discover-page) .chip {
    margin: 0;
    max-width: 100%;
    white-space: normal;
    overflow-wrap: break-word;
}

[data-testid="stVerticalBlockBorderWrapper"]:has(.discover-card) [data-testid="stHorizontalBlock"] {
    flex-wrap: nowrap;
    width: 100%;
}

[data-testid="stVerticalBlockBorderWrapper"]:has(.discover-card) .stButton > button {
    width: 100%;
    white-space: normal;
    min-height: 2.4rem;
}

.main:has(.discover-page) .status-line {
    margin: 0.15rem 0 0 0;
}

.main:has(.discover-page) .match-company,
.main:has(.discover-page) .match-location {
    overflow-wrap: anywhere;
    white-space: normal;
}

.main:has(.discover-page) .match-company {
    font-size: 0.92rem;
}

.main:has(.discover-page) .match-location,
.main:has(.discover-page) .discover-card-body .hero-lead {
    margin: 0.12rem 0 0 0;
    color: var(--muted);
    font-size: 0.84rem;
    line-height: 1.35;
}

.discover-sources .adzuna-credit,
.discover-sources .adzuna-apply {
    margin: 0;
}

.discover-score {
    margin-top: 0.35rem;
}

.adzuna-credit {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    box-sizing: border-box;
    min-width: 116px;
    min-height: 23px;
    margin: 0.45rem 0.4rem 0.2rem 0;
    padding: 0 0.7rem;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--badge-bg);
    color: var(--badge-ink);
    font-size: 0.95rem;
    font-weight: 700;
    line-height: 1;
    text-decoration: none;
}

.adzuna-apply {
    display: inline-flex;
    align-items: center;
    min-height: 23px;
    color: var(--accent-text);
    font-size: 0.86rem;
    font-weight: 650;
}

.saved-footer {
    margin-top: 0.45rem;
    margin-bottom: 0.15rem;
}

.saved-summary-line {
    margin: 0 0 0.2rem 0;
    color: var(--text-secondary);
    font-size: var(--text-sm);
    line-height: 1.4;
}

.saved-reason,
.saved-quality {
    margin: 0.05rem 0 0.15rem 0;
    color: var(--text-muted);
    font-size: 0.84rem;
    line-height: 1.35;
}

.saved-card-body .match-company,
.saved-card-body .match-location,
.saved-card-body .saved-date {
    margin: 0.08rem 0;
}

.main:has(.saved-page) .match-title.saved-card {
    font-size: 1.05rem;
    line-height: 1.3;
    overflow-wrap: anywhere;
}

.main:has(.saved-page) [data-testid="stVerticalBlockBorderWrapper"]:has(.saved-card) > div {
    padding: 0.85rem 0.9rem 0.75rem 0.9rem;
}

.main:has(.saved-page) [data-testid="stVerticalBlockBorderWrapper"]:has(.saved-card) .stButton > button {
    width: 100%;
    white-space: normal;
}

.main:has(.saved-page) [data-testid="stVerticalBlockBorderWrapper"]:has(.saved-card) [data-testid="stHorizontalBlock"] {
    flex-wrap: wrap;
    gap: 0.4rem;
}

[data-testid="stVerticalBlockBorderWrapper"]:has(.saved-card) .insight-panel {
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
    margin-top: 0.7rem;
}

.discover-more {
    margin: 0.15rem 0 0.45rem 0;
    color: var(--muted);
    font-size: 0.82rem;
}

.prep-note,
.prep-count,
.prep-task-note {
    margin: 0.15rem 0 0.75rem 0;
    color: var(--text-secondary);
    line-height: 1.45;
}

.prep-done {
    margin: 0 0 0.8rem 0;
    color: var(--ok);
    font-weight: 650;
}

.prep-job {
    margin: 0.15rem 0;
    overflow-wrap: anywhere;
}

.prep-source {
    color: var(--text-muted);
}

.prep-next {
    margin: 0.85rem 0 0.7rem 0;
    padding: 0.75rem 0.9rem;
    border-radius: 12px;
    background: var(--surface-soft);
    color: var(--ink);
}

.bar-row {
    display: grid;
    grid-template-columns: 9.5rem 2rem 1fr;
    gap: 0.75rem;
    align-items: center;
    margin: 0.55rem 0;
}

.bar-label,
.bar-count {
    color: var(--chart-text);
    font-size: 0.92rem;
}

.bar-count {
    text-align: right;
    font-weight: 650;
}

.bar-track {
    display: block;
    height: 10px;
    border-radius: 999px;
    background: var(--lavender);
    overflow: hidden;
}

.bar-fill {
    display: block;
    height: 100%;
    border-radius: 999px;
    background: var(--accent);
}

.bar-fill-exact {
    background: var(--fill-strong);
}

.bar-fill-semantic {
    background: var(--accent);
}

.bar-fill-missing {
    background: var(--chip-line);
}

.chart-caption {
    margin: 0 0 0.85rem 0;
    color: var(--muted);
    font-size: 0.92rem;
    line-height: 1.45;
}

.score-chart {
    display: grid;
    grid-template-columns: 1.4rem 1fr;
    gap: 0.45rem;
    align-items: stretch;
    min-height: 220px;
}

.scale-max {
    align-self: start;
    color: var(--muted);
    font-size: 0.75rem;
    line-height: 1;
}

.score-plot {
    position: relative;
    display: flex;
    align-items: stretch;
    gap: 0.55rem;
    min-height: 200px;
    padding-top: 0.2rem;
    border-bottom: 1px solid var(--line);
    background: var(--chart-bg);
    color: var(--chart-text);
}

.gridline {
    position: absolute;
    left: 0;
    right: 0;
    height: 1px;
    background: var(--line);
    pointer-events: none;
}

.gridline-top {
    top: 0;
}

.gridline-mid {
    top: 50%;
}

.score-column {
    position: relative;
    z-index: 1;
    display: flex;
    flex: 1 1 0;
    flex-direction: column;
    align-items: center;
    min-width: 0;
    height: 100%;
}

.column-value {
    order: 1;
    color: var(--ink);
    font-size: 0.82rem;
    font-weight: 650;
    line-height: 1.2;
}

.column-track {
    order: 2;
    display: flex;
    flex: 1 1 auto;
    align-items: flex-end;
    width: 100%;
    max-width: 2.4rem;
    margin-top: 0.3rem;
}

.column-bar {
    display: block;
    width: 100%;
    border-radius: 7px 7px 2px 2px;
    background: var(--accent);
}

.column-label {
    order: 3;
    margin-top: 0.45rem;
    color: var(--chart-text);
    font-size: 0.75rem;
    line-height: 1.2;
    text-align: center;
}

.stacked-bar {
    display: flex;
    width: 100%;
    height: 16px;
    overflow: hidden;
    border-radius: 999px;
    background: var(--lavender);
}

.stack-segment {
    display: block;
    height: 100%;
}

.stack-exact,
.legend-swatch.stack-exact {
    background: var(--fill-strong);
}

.stack-semantic,
.legend-swatch.stack-semantic {
    background: var(--accent);
}

.stack-missing,
.legend-swatch.stack-missing {
    background: var(--chip-line);
}

.chart-legend {
    list-style: none;
    margin: 1rem 0 0 0;
    padding: 0;
}

.legend-item {
    display: grid;
    grid-template-columns: 0.7rem 1fr auto auto;
    gap: 0.55rem;
    align-items: center;
    margin: 0.45rem 0;
    color: var(--chart-text);
    font-size: 0.92rem;
}

.legend-swatch {
    width: 0.7rem;
    height: 0.7rem;
    border-radius: 999px;
}

.legend-count,
.legend-share {
    font-variant-numeric: tabular-nums;
}

.legend-share {
    min-width: 3.2rem;
    color: var(--muted);
    text-align: right;
}

[data-testid="stVerticalBlockBorderWrapper"]:has(.chart-card) {
    height: 100%;
}

.profile-overview-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 8.5rem;
    gap: 1.5rem;
    align-items: center;
}

.profile-fact {
    margin: 0.15rem 0 0.45rem 0;
    color: var(--navy);
    font-size: 1.35rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    line-height: 1.3;
}

.progress-ring {
    position: relative;
    width: 8.5rem;
    height: 8.5rem;
    margin-left: auto;
}

.progress-ring svg {
    width: 100%;
    height: 100%;
    display: block;
}

.ring-track,
.ring-value {
    fill: none;
    stroke-width: 10;
}

.ring-track {
    stroke: var(--lavender);
}

.ring-value {
    stroke: var(--accent-text);
    stroke-linecap: round;
    transform: rotate(-90deg);
    transform-origin: 60px 60px;
}

.ring-label {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--navy);
    font-size: 1.35rem;
    font-weight: 700;
}

.profile-overview-grid {
    display: grid;
    grid-template-columns: minmax(0, 1.5fr) minmax(11rem, 0.7fr);
    gap: 0.85rem 1.4rem;
    align-items: center;
}

.profile-identity {
    display: flex;
    gap: 0.9rem;
    align-items: center;
    min-width: 0;
}

.profile-id-copy {
    min-width: 0;
}

.profile-facts {
    display: flex;
    flex-wrap: wrap;
    gap: 0.2rem 1rem;
    margin-top: 0.35rem;
}

.profile-facts .detail-line {
    margin: 0;
}

.profile-completion-panel {
    min-width: 0;
    padding: 0.75rem 0.85rem;
    border: 1px solid var(--line);
    border-radius: 14px;
    background: var(--surface-soft);
}

.profile-highlights {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.75rem 1.2rem;
    margin-top: 0.95rem;
}

.profile-highlight {
    min-width: 0;
}

.avatar {
    width: 3.1rem;
    height: 3.1rem;
    border-radius: 999px;
    background: var(--fill-strong);
    color: var(--white);
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    flex: 0 0 auto;
}

.profile-percent,
.score-hero {
    margin: 0.1rem 0;
    color: var(--navy);
    font-weight: 700;
    letter-spacing: -0.03em;
    line-height: 1.1;
}

.profile-percent {
    font-size: 1.35rem;
}

.builder-steps {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin: 0 0 0.8rem 0;
}

.builder-step {
    border-radius: 999px;
    padding: 0.28rem 0.7rem;
    background: var(--step-bg);
    color: var(--navy);
    font-size: 0.82rem;
}

.builder-step.current {
    background: var(--step-current-bg);
    color: var(--step-current-ink);
    font-weight: 700;
}

.completion-help {
    margin: 0.15rem 0 0.45rem 0;
    color: var(--muted);
    line-height: 1.45;
}

.completion-criteria {
    margin: 0.2rem 0 0.15rem 1.1rem;
    color: var(--ink);
    line-height: 1.55;
}

.completion-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.65rem;
    margin-top: 0.85rem;
}

.completion-item {
    display: grid;
    grid-template-columns: 1.55rem minmax(0, 1fr);
    grid-template-rows: auto auto;
    column-gap: 0.6rem;
    row-gap: 0.1rem;
    align-items: center;
    min-width: 0;
    padding: 0.7rem 0.75rem;
    border: 1px solid var(--line);
    border-radius: 12px;
    background: var(--completion-open);
}

.completion-icon {
    grid-row: 1 / span 2;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 1.55rem;
    height: 1.55rem;
    border-radius: 999px;
    color: var(--navy);
}

.completion-icon svg {
    width: 0.95rem;
    height: 0.95rem;
    fill: none;
    stroke: currentColor;
    stroke-width: 1.8;
    stroke-linecap: round;
    stroke-linejoin: round;
}

.completion-name {
    color: var(--navy);
    font-size: 0.92rem;
    font-weight: 650;
    line-height: 1.3;
    overflow-wrap: break-word;
}

.completion-state {
    color: var(--muted);
    font-size: 0.8rem;
    font-style: normal;
    line-height: 1.3;
}

.completion-filled {
    background: var(--surface-soft);
    border-color: var(--completion-line);
}

.completion-filled .completion-icon {
    background: var(--completion-ok-bg);
    color: var(--ok);
}

.completion-open .completion-icon {
    background: var(--surface);
    border: 1px solid var(--line);
    color: var(--muted);
}

[data-testid="stExpander"] {
    border: 1px solid var(--line) !important;
    border-radius: 12px !important;
    background: var(--surface);
}

.score-hero {
    font-size: 2.1rem;
}

.progress-track {
    display: block;
    height: 8px;
    margin: 0.45rem 0 0.15rem 0;
    border-radius: 999px;
    background: var(--lavender);
    overflow: hidden;
}

.progress-fill {
    display: block;
    height: 100%;
    border-radius: 999px;
    background: var(--accent);
}

.sidebar-meta {
    overflow-wrap: anywhere;
}

.resume-heading {
    margin: 0.4rem 0 0.2rem 0;
}

.resume-filename {
    overflow-wrap: break-word;
    word-break: normal;
}

.resume-metrics,
.resume-checks {
    display: grid;
    gap: 0.7rem;
    margin: 0.8rem 0 0.9rem 0;
}

.resume-metrics {
    grid-template-columns: repeat(3, minmax(0, 1fr));
}

.resume-checks {
    grid-template-columns: repeat(2, minmax(0, 1fr));
}

.resume-overview,
.resume-privacy {
    max-width: 68ch;
    color: var(--text-secondary);
}

.resume-limit {
    margin: 0.1rem 0 0.55rem 0;
    color: var(--muted);
}

.resume-related {
    margin: 0.35rem 0;
    padding: 0.55rem 0.7rem;
    border: 1px solid var(--line);
    border-radius: 12px;
    background: var(--surface-soft);
    color: var(--text-secondary);
}

.main:has(.resume-page) [data-testid="stFileUploader"] {
    max-width: 100%;
}

.main:has(.resume-page) [data-testid="stFileUploader"] section {
    max-width: 100%;
}

.resume-metric,
.resume-check {
    min-width: 0;
    border: 1px solid var(--line);
    border-radius: 14px;
    background: var(--surface);
    padding: 0.8rem 0.85rem 0.75rem 0.85rem;
    box-shadow: var(--shadow);
}

.resume-percent {
    margin: 0.15rem 0;
    color: var(--ink);
    font-size: 1.45rem;
    font-weight: 700;
    letter-spacing: -0.03em;
    line-height: 1.1;
}

.resume-health-label {
    margin: 0.2rem 0 0.35rem 0;
    font-size: 1.2rem;
    font-weight: 700;
    letter-spacing: -0.03em;
    color: var(--ink);
}

.resume-health-good { color: var(--score-high); }
.resume-health-mid { color: var(--accent-text); }
.resume-health-attention { color: var(--muted); }

.resume-note {
    margin: 0.35rem 0 0.8rem 0;
    color: var(--muted);
}

.resume-mark {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.15rem;
    height: 1.15rem;
    margin-right: 0.4rem;
    border-radius: 999px;
    background: var(--lavender);
    color: var(--accent-text);
    font-size: 0.72rem;
    font-weight: 700;
    vertical-align: 0.05rem;
}

.resume-found .resume-mark {
    background: var(--resume-found-bg);
    color: var(--score-high);
}

.main:has(.resume-page) [data-testid="stRadio"] [role="radiogroup"] {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.55rem;
    width: 100%;
}

.main:has(.resume-page) [data-testid="stRadio"] label {
    display: flex;
    align-items: center;
    min-height: 2.75rem;
    margin: 0;
    padding: 0.7rem 0.9rem;
    border: 1px solid var(--line);
    border-radius: 14px;
    background: var(--surface);
    color: var(--navy);
}

.main:has(.resume-page) [data-testid="stRadio"] label:has(input:checked) {
    background: var(--lavender);
    border-color: var(--accent);
    color: var(--accent-text);
    box-shadow: inset 0 0 0 1px var(--accent);
}

.resume-metric-value {
    font-size: 1.35rem;
}

.resume-state {
    margin: 0.15rem 0 0.35rem 0;
    color: var(--accent-text);
    font-size: 0.92rem;
    font-weight: 700;
}

.resume-found .resume-state {
    color: var(--ok);
}

.resume-missing .resume-state,
.resume-incomplete .resume-state {
    color: var(--warn);
}

.resume-check .hero-lead,
.resume-list {
    overflow-wrap: break-word;
    word-break: normal;
}

.resume-list {
    margin: 0.2rem 0 0.4rem 1.1rem;
    color: var(--ink);
}

.coverage-track {
    height: 8px;
    margin: 0.2rem 0 0.7rem 0;
    background: var(--lavender);
    border-radius: 999px;
    overflow: hidden;
}

.coverage-fill {
    height: 100%;
    background: var(--accent);
}

.main:has(.home-dashboard) [data-testid="stHorizontalBlock"]:has(.home-panel) {
    align-items: stretch;
}

.main:has(.home-dashboard) [data-testid="stColumn"]:has(.home-panel) {
    display: flex;
    min-width: 0;
}

.main:has(.home-dashboard) [data-testid="stVerticalBlockBorderWrapper"]:has(.home-panel) {
    flex: 1 1 auto;
    width: 100%;
    height: 100%;
    background: var(--surface) !important;
    border: 1px solid var(--line) !important;
    border-radius: var(--radius-card) !important;
    box-shadow: var(--shadow);
}

.main:has(.home-dashboard) [data-testid="stVerticalBlockBorderWrapper"]:has(.home-panel) > div {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-width: 0;
}

.main:has(.home-dashboard) [data-testid="stVerticalBlockBorderWrapper"]:has(.home-saved) [data-testid="stElementContainer"]:has(.stButton) {
    margin-top: auto;
}

.main:has(.home-dashboard) .home-panel {
    color: var(--navy);
}

.main:has(.home-dashboard) [data-testid="stVerticalBlockBorderWrapper"]:has(.home-panel) .match-title,
.main:has(.home-dashboard) [data-testid="stVerticalBlockBorderWrapper"]:has(.home-panel) .home-ring-label {
    color: var(--navy);
}

.main:has(.home-dashboard) [data-testid="stVerticalBlockBorderWrapper"]:has(.home-panel) .match-company,
.main:has(.home-dashboard) [data-testid="stVerticalBlockBorderWrapper"]:has(.home-panel) .match-location,
.main:has(.home-dashboard) [data-testid="stVerticalBlockBorderWrapper"]:has(.home-panel) .saved-date,
.main:has(.home-dashboard) [data-testid="stVerticalBlockBorderWrapper"]:has(.home-panel) .hero-lead {
    color: var(--muted);
}

.home-match-card,
.home-saved-card {
    min-width: 0;
    margin: 0 0 0.35rem 0;
    padding: 0.85rem 0.9rem 0.75rem 0.9rem;
    border: 1px solid var(--line);
    border-radius: var(--radius-card);
    background: var(--home-card);
    box-shadow: var(--shadow-soft);
    transition: transform 0.16s ease, border-color 0.16s ease, box-shadow 0.16s ease;
}

.home-match-card:hover,
.home-saved-card:hover {
    transform: translateY(-2px);
    border-color: var(--control-line);
    box-shadow: var(--shadow);
}

.home-match-top,
.home-saved-top {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    min-width: 0;
}

.home-match-copy {
    flex: 1 1 auto;
    min-width: 0;
}

.main:has(.home-dashboard) .home-match-copy .match-title {
    overflow-wrap: break-word;
    word-break: normal;
    font-size: 1.02rem;
    line-height: 1.3;
}

.home-avatar {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex: 0 0 auto;
    width: 2.3rem;
    height: 2.3rem;
    border-radius: 999px;
    background: var(--lavender);
    border: 1px solid var(--line);
    color: var(--accent-text);
    font-size: 0.78rem;
    font-weight: 700;
}

.home-bookmark {
    flex: 0 0 auto;
    color: var(--accent-text);
}

.home-icon {
    width: 0.95rem;
    height: 0.95rem;
    fill: none;
    stroke: currentColor;
    stroke-width: 1.7;
    stroke-linejoin: round;
    stroke-linecap: round;
    vertical-align: -0.15rem;
}

.home-divider {
    margin: 0.7rem 0 0.55rem 0;
    border: 0;
    border-top: 1px solid var(--line);
}

.home-chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    margin-top: 0.75rem;
}

.home-chip {
    max-width: 100%;
    padding: 0.18rem 0.5rem;
    border-radius: 999px;
    background: var(--lavender);
    border: 1px solid var(--line);
    color: var(--accent-text);
    font-size: 0.75rem;
    overflow-wrap: break-word;
    word-break: normal;
}

.home-ring {
    position: relative;
    flex: 0 0 auto;
    width: 4.4rem;
    height: 4.4rem;
}

.home-ring svg {
    width: 100%;
    height: 100%;
    transform: rotate(-90deg);
}

.home-ring-track,
.home-ring-value {
    fill: none;
    stroke-width: 5;
}

.home-ring-track {
    stroke: var(--line);
}

.home-ring-value {
    stroke: var(--ring, var(--score-low));
    stroke-linecap: round;
}

.home-ring-high { --ring: var(--score-high); }
.home-ring-mid { --ring: var(--score-mid); }
.home-ring-blue { --ring: var(--score-fair); }
.home-ring-low { --ring: var(--score-low); }

.home-ring-label {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.82rem;
    font-weight: 700;
}

.home-score-text {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
}

.main:has(.home-dashboard) [data-testid="stVerticalBlockBorderWrapper"]:has(.home-panel) .stButton > button {
    width: 100%;
    border: 1px solid var(--line) !important;
    border-radius: 999px !important;
    background: var(--lavender) !important;
    color: var(--accent-text) !important;
    font-weight: 650;
    white-space: normal;
}

@media (max-width: 820px) {
    .main .block-container {
        padding-left: 1rem;
        padding-right: 1rem;
        padding-top: 1.5rem;
    }

    h1 {
        font-size: 1.45rem;
    }

    .step-card {
        min-height: 0;
    }

    .match-title,
    .hero-title {
        font-size: 1.25rem;
    }

    [data-testid="stVerticalBlockBorderWrapper"]:has(.saved-controls) [data-testid="stHorizontalBlock"],
    [data-testid="stVerticalBlockBorderWrapper"]:has(.match-controls) [data-testid="stHorizontalBlock"],
    [data-testid="stVerticalBlockBorderWrapper"]:has(.home-actions) [data-testid="stHorizontalBlock"],
    [data-testid="stVerticalBlockBorderWrapper"]:has(.auth-card) [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap;
    }

    [data-testid="stVerticalBlockBorderWrapper"]:has(.match-card) [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap;
    }

    [data-testid="stColumn"]:has(.score-label) {
        flex: 1 1 46% !important;
        min-width: 46% !important;
        width: auto !important;
    }

    .main:has(.home-dashboard) [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap;
    }

    .main:has(.home-dashboard) [data-testid="stColumn"] {
        flex: 1 1 46% !important;
        min-width: 46% !important;
        width: auto !important;
    }

    .main:has(.home-dashboard) [data-testid="stColumn"]:has(.chart-card) {
        flex: 1 1 100% !important;
        min-width: 100% !important;
    }

    .main:has(.home-dashboard) [data-testid="stColumn"]:has(.home-panel) {
        flex: 1 1 100% !important;
        min-width: 100% !important;
        width: 100% !important;
    }

    .column-label {
        font-size: 0.68rem;
    }

    .bar-row {
        grid-template-columns: 7.2rem 1.6rem 1fr;
    }

    .main:has(.profile-dashboard) [data-testid="stHorizontalBlock"],
    .main:has(.discover-page) [data-testid="stVerticalBlockBorderWrapper"]:not(:has(.discover-card)) [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap;
    }

    .main:has(.profile-dashboard) [data-testid="stColumn"],
    .main:has(.discover-page) [data-testid="stVerticalBlockBorderWrapper"]:not(:has(.discover-card)) [data-testid="stColumn"] {
        flex: 1 1 100% !important;
        min-width: 100% !important;
        width: auto !important;
    }

    .profile-overview-grid,
    .profile-highlights {
        grid-template-columns: 1fr;
    }

    .progress-ring {
        margin-left: 0;
    }

    .completion-grid,
    .resume-checks,
    .resume-metrics {
        grid-template-columns: 1fr;
    }

    .main:has(.resume-page) [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap;
    }

    .main:has(.resume-page) [data-testid="stColumn"] {
        flex: 1 1 100% !important;
        min-width: 100% !important;
        width: auto !important;
    }

    .main:has(.resume-page) [data-testid="stRadio"] [role="radiogroup"] {
        grid-template-columns: 1fr;
    }
}

.main:has(.home-dashboard) [data-testid="stVerticalBlock"]:has(.home-actions) .stButton > button,
.main:has(.home-dashboard) [data-testid="stVerticalBlock"][data-test-scroll-behavior]:has(.home-actions) .stButton > button {
    width: 100%;
    min-height: 2.6rem;
    white-space: normal;
}

@media (max-width: 1180px) {
    .main:has(.home-dashboard) [data-testid="stHorizontalBlock"]:has(.kpi-card),
    .main:has(.home-dashboard) [data-testid="stHorizontalBlock"]:has(.home-actions) {
        flex-wrap: wrap;
    }

    .main:has(.home-dashboard) [data-testid="stColumn"]:has(.kpi-card),
    .main:has(.home-dashboard) [data-testid="stVerticalBlock"]:has(.home-actions) [data-testid="stColumn"] {
        flex: 1 1 calc(50% - 0.8rem) !important;
        min-width: calc(50% - 0.8rem) !important;
        width: auto !important;
    }
}

@media (max-width: 1100px) {
    .main:has(.discover-page) [data-testid="stVerticalBlock"]:has(.discover-grid):not(:has([data-testid="stVerticalBlock"] .discover-grid)) {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .resume-checks {
        grid-template-columns: 1fr;
    }
}

@media (max-width: 680px) {
    .main:has(.match-page) [data-testid="stVerticalBlockBorderWrapper"]:has(.match-overview) [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap;
    }

    .main:has(.match-page) [data-testid="stVerticalBlockBorderWrapper"]:has(.match-overview) [data-testid="stColumn"],
    .main:has(.match-page) [data-testid="stColumn"]:has(.score-label) {
        flex: 1 1 100% !important;
        min-width: 0 !important;
        width: 100% !important;
    }

    .main:has(.discover-page) [data-testid="stVerticalBlock"]:has(.discover-grid):not(:has([data-testid="stVerticalBlock"] .discover-grid)) {
        grid-template-columns: minmax(0, 1fr);
    }

    .main:has(.discover-page) [data-testid="stVerticalBlockBorderWrapper"]:not(:has(.discover-card)) [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap;
    }

    .main:has(.discover-page) [data-testid="stVerticalBlockBorderWrapper"]:not(:has(.discover-card)) [data-testid="stColumn"] {
        flex: 1 1 100% !important;
        min-width: 0 !important;
        width: 100% !important;
    }
}

@media (max-width: 390px) {
    .main:has(.discover-page) [data-testid="stVerticalBlock"]:has(.discover-grid):not(:has([data-testid="stVerticalBlock"] .discover-grid)) {
        grid-template-columns: minmax(0, 1fr);
    }

    .main:has(.discover-page) [data-testid="stVerticalBlockBorderWrapper"]:not(:has(.discover-card)) [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap;
    }

    .main:has(.discover-page) [data-testid="stVerticalBlockBorderWrapper"]:not(:has(.discover-card)) [data-testid="stColumn"] {
        flex: 1 1 100% !important;
        min-width: 0 !important;
        width: 100% !important;
    }

    .main:has(.discover-page) [data-testid="stSelectbox"],
    .main:has(.discover-page) [data-testid="stTextInput"],
    .main:has(.discover-page) .stButton > button {
        max-width: 100%;
    }

    .main:has(.discover-page) label {
        white-space: normal;
        overflow-wrap: break-word;
    }
}

[data-testid="stElementContainer"]:has(iframe[height="0"]) {
    height: 0 !important;
    min-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
}

@media (max-width: 560px) {
    .main:has(.home-dashboard) [data-testid="stColumn"]:has(.kpi-card) {
        flex: 1 1 100% !important;
        min-width: 100% !important;
        width: auto !important;
    }
}

@media (max-width: 680px) {
    [data-testid="stVerticalBlockBorderWrapper"]:has(.discover-card) [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap;
    }

    [data-testid="stVerticalBlockBorderWrapper"]:has(.discover-card) [data-testid="stColumn"] {
        flex: 1 1 100% !important;
        min-width: 0 !important;
        width: 100% !important;
    }

    .main:has(.auth-card) [data-testid="stColumn"] {
        flex: 1 1 100% !important;
        min-width: 0 !important;
        width: 100% !important;
    }
}

@media (max-width: 820px) {
    [data-testid="stVerticalBlockBorderWrapper"]:has(.prep-plan) [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap;
    }

    [data-testid="stVerticalBlockBorderWrapper"]:has(.prep-plan) [data-testid="stColumn"] {
        flex: 1 1 100% !important;
        min-width: 0 !important;
        width: 100% !important;
    }
}
</style>
"""


_THEME_SYNC = """
<script>
(() => {
  const parentWindow = window.parent;
  const doc = parentWindow.document;
  const sync = () => {
    const app = doc.querySelector(".stApp");
    if (!app) {
      return;
    }
    const scheme = parentWindow.getComputedStyle(app).colorScheme;
    const theme = scheme === "dark" ? "dark" : "light";
    if (doc.documentElement.getAttribute("data-theme") !== theme) {
      doc.documentElement.setAttribute("data-theme", theme);
    }
  };
  sync();
  if (parentWindow.__ajThemeSync) {
    return;
  }
  const app = doc.querySelector(".stApp");
  if (app) {
    const observer = new parentWindow.MutationObserver(sync);
    observer.observe(app, { attributes: true, attributeFilter: ["class", "style"] });
  }
  parentWindow.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    parentWindow.setTimeout(sync, 50);
  });
  parentWindow.__ajThemeSync = true;
})();
</script>
"""


def inject_theme() -> None:
    """Apply the shared colours on every page."""
    st.markdown(CSS, unsafe_allow_html=True)
    st.components.v1.html(_THEME_SYNC, height=0, width=0)
