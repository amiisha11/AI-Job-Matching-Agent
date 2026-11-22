"""Navy, lavender, and white styling for the Streamlit screens."""

import streamlit as st

CSS = """
<style>
:root {
    --navy: #1B2A4A;
    --sidebar: #1B2436;
    --lavender: #E7E4F8;
    --accent: #6D62C8;
    --white: #FFFFFF;
    --ink: #172033;
    --muted: #64748B;
    --line: #E2E8F0;
    --page: #F4F2FB;
    --ok: #2F7D4A;
    --warn: #A16207;
    --danger: #B42318;
    --shadow: 0 8px 22px rgba(23, 32, 51, 0.05);
}

html, body, .stApp {
    background: var(--page);
    color: var(--ink);
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 16px;
}

.main .block-container {
    max-width: 1120px;
    padding-top: 1.8rem;
    padding-bottom: 3rem;
    padding-left: 1.8rem;
    padding-right: 1.8rem;
}

.main [data-testid="stVerticalBlock"] {
    gap: 1.15rem;
}

[data-testid="stHorizontalBlock"] {
    gap: 1.2rem;
}

h1 {
    color: var(--ink);
    font-size: 1.7rem;
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
    margin: 0.2rem 0 1.35rem 0;
    color: var(--muted);
    font-size: 1.05rem;
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
    color: var(--accent);
    font-size: 0.78rem;
    font-weight: 650;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

.step-card,
.hero-copy,
.note {
    background: var(--white);
    border: 1px solid var(--line);
    border-radius: 16px;
    box-shadow: var(--shadow);
}

.step-card {
    padding: 1.5rem 1.4rem 1.35rem 1.4rem;
    min-height: 11rem;
    border-radius: 18px;
    box-shadow: 0 10px 28px rgba(27, 42, 74, 0.06);
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
    background: var(--white);
    border: 1px solid var(--line) !important;
    border-radius: 16px !important;
    box-shadow: var(--shadow);
}

[data-testid="stVerticalBlockBorderWrapper"] > div {
    padding: 1.35rem 1.4rem 1.2rem 1.4rem;
}

[data-testid="stMetric"] {
    background: var(--white);
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 1.15rem 1.2rem 1rem 1.2rem;
    box-shadow: 0 10px 28px rgba(27, 42, 74, 0.06);
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
    background: var(--white);
    color: var(--ink);
    border-color: #D9D4EE !important;
    border-radius: 12px !important;
    min-height: 2.75rem;
}

[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus,
[data-testid="stSelectbox"] div[data-baseweb="select"] > div:focus-within,
[data-testid="stMultiSelect"] div[data-baseweb="select"] > div:focus-within {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(109, 98, 200, 0.16);
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
    border-radius: 10px;
    min-height: 2.7rem;
    padding: 0.45rem 1.05rem;
    font-weight: 600;
    transition: background 0.15s ease, border-color 0.15s ease;
}

.stButton > button {
    background: var(--white);
    color: var(--ink);
    border: 1px solid #D9D4EE;
}

.stButton > button:hover {
    border-color: var(--accent);
    color: var(--ink);
    background: #F4F2FB;
}

.stButton > button[kind="primary"],
.stFormSubmitButton > button {
    background: var(--accent);
    color: var(--white);
    border: 1px solid var(--accent);
}

.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button:hover {
    background: #584EB4;
    border-color: #584EB4;
    color: var(--white);
}

.stFormSubmitButton {
    margin-top: 0.35rem;
}

.stFormSubmitButton > button {
    min-width: 11rem;
}

[data-testid="stAlert"] {
    border-radius: 14px !important;
    border: 1px solid var(--line) !important;
}

.note {
    padding: 0.95rem 1.05rem;
    margin: 0.35rem 0 0.2rem 0;
    color: var(--ink);
    line-height: 1.6;
    box-shadow: none;
    background: #F8F7FC;
}

.chip-row {
    margin: 0.15rem 0 0.35rem 0;
}

.chip {
    display: inline-block;
    margin: 0 0.45rem 0.45rem 0;
    padding: 0.32rem 0.8rem;
    border-radius: 999px;
    font-size: 0.92rem;
    line-height: 1.4;
}

.chip-exact {
    background: var(--navy);
    color: var(--white);
}

.chip-semantic {
    background: var(--lavender);
    color: var(--navy);
}

.chip-missing {
    background: var(--white);
    color: var(--navy);
    border: 1px solid #C9C4E8;
}

[data-testid="stSidebar"] {
    background: var(--sidebar);
    border-right: none;
    min-width: 260px !important;
    width: 260px !important;
}

[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] div {
    color: #F7F5FF;
}

[data-testid="stSidebarUserContent"] {
    padding-top: 0.4rem;
}

[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
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
    color: #E7E4F8 !important;
    font-size: 0.84rem;
    line-height: 1.4;
}

[data-testid="stSidebar"] [data-testid="stRadio"] {
    margin-bottom: 0.4rem;
}

[data-testid="stSidebar"] [role="radiogroup"] {
    gap: 0.3rem;
}

[data-testid="stSidebar"] [role="radiogroup"] > label {
    padding: 0.68rem 0.8rem;
    border-radius: 12px;
    margin: 0;
    gap: 0;
}

[data-testid="stSidebar"] [role="radiogroup"] input {
    position: absolute;
    opacity: 0;
    width: 1px;
    height: 1px;
}

[data-testid="stSidebar"] [data-testid="stRadioOption"] > div > div:first-child {
    display: none !important;
}

[data-testid="stSidebar"] [role="radiogroup"] > label:hover {
    background: rgba(231, 228, 248, 0.1);
}

[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked),
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
    background: rgba(231, 228, 248, 0.2) !important;
    border-radius: 12px;
    box-shadow: inset 3px 0 0 #C9C4E8;
}

[data-testid="stSidebar"] .stButton > button {
    width: 100%;
    justify-content: flex-start;
    background: transparent;
    color: #F7F5FF !important;
    border: 1px solid rgba(231, 228, 248, 0.28);
    border-radius: 12px;
    margin-top: 0.35rem;
}

[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(231, 228, 248, 0.12);
    color: #F7F5FF !important;
    border-color: rgba(231, 228, 248, 0.5);
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
    background: #C9F2D6;
}

.status-down {
    background: #F0C9C4;
}

.sidebar-session {
    margin-top: auto;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(231, 228, 248, 0.2);
    border-radius: 14px;
    padding: 0.95rem 1rem 0.8rem 1rem;
}

.sidebar-kicker {
    margin: 0 0 0.3rem 0;
    color: #C9C4E8 !important;
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
    background: var(--white);
    border: 1px solid var(--line) !important;
    border-radius: 18px !important;
    box-shadow: 0 10px 28px rgba(27, 42, 74, 0.06);
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
}

.match-company {
    margin: 0;
    color: var(--ink);
    font-size: 1rem;
    font-weight: 600;
}

.match-location {
    margin: 0.2rem 0 0.15rem 0;
    color: var(--muted);
    font-size: 0.95rem;
}

[data-testid="stColumn"]:has(.score-label) {
    background: #F8F7FC;
    border: 1px solid var(--line);
    border-radius: 14px;
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
    background: #F3F1FB;
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 1rem 1.1rem;
    margin: 0.15rem 0 0.85rem 0;
    color: var(--ink);
    line-height: 1.65;
}

[data-testid="stVerticalBlockBorderWrapper"]:has(.match-card) .stButton > button {
    min-width: 9.5rem;
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
    background: var(--white);
    border: 1px solid var(--line) !important;
    border-radius: 18px !important;
    box-shadow: 0 10px 28px rgba(27, 42, 74, 0.06);
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
    background: var(--navy) !important;
    border-radius: 999px !important;
    border: none !important;
}

.main:has(.profile-builder) [data-baseweb="tag"] span {
    color: var(--white) !important;
}

.main:has(.auth-card) .block-container {
    max-width: 640px;
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
    background: #F3F1FB;
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
    display: grid;
    height: auto;
    overflow: visible;
}

.main:has(.home-dashboard) [data-testid="stVerticalBlockBorderWrapper"]:has(.kpi-card)::before {
    content: "";
    grid-area: 1 / 1;
    width: 100%;
    aspect-ratio: 1 / 1;
    pointer-events: none;
}

.main:has(.home-dashboard) [data-testid="stVerticalBlockBorderWrapper"]:has(.kpi-card) > div {
    grid-area: 1 / 1;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    height: auto;
    min-height: 100%;
    box-sizing: border-box;
    padding: 1.15rem 1.1rem 1rem 1.1rem;
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
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 1rem 1.1rem;
    align-items: stretch;
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
    display: grid;
    height: 100%;
    overflow: visible;
}

.main:has(.discover-page) [data-testid="stVerticalBlockBorderWrapper"]:has(.discover-card)::before {
    content: "";
    grid-area: 1 / 1;
    width: 100%;
    aspect-ratio: 1 / 1.05;
    pointer-events: none;
}

.main:has(.discover-page) [data-testid="stVerticalBlockBorderWrapper"]:has(.discover-card) > div {
    grid-area: 1 / 1;
    display: flex;
    flex-direction: column;
    height: auto;
    min-height: 100%;
    box-sizing: border-box;
    padding: 1.05rem 1rem 0.95rem 1rem;
}

.discover-card {
    overflow-wrap: break-word;
    word-break: normal;
    font-size: 1.08rem;
    line-height: 1.3;
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

.main:has(.discover-page) .match-company,
.main:has(.discover-page) .match-location {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.discover-score {
    margin-top: 0.65rem;
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
    border: 1px solid #E5E7F0;
    border-radius: 8px;
    background: #FFFFFF;
    color: #202B45;
    font-size: 0.95rem;
    font-weight: 700;
    line-height: 1;
    text-decoration: none;
}

.adzuna-apply {
    display: inline-flex;
    align-items: center;
    min-height: 23px;
    color: #6D62C8;
    font-size: 0.86rem;
    font-weight: 650;
}

.saved-footer {
    margin-top: auto;
    margin-bottom: 0.35rem;
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
.prep-count {
    margin: 0.15rem 0 0.75rem 0;
    color: var(--muted);
    line-height: 1.45;
}

.prep-done {
    margin: 0 0 0.8rem 0;
    color: var(--navy);
    font-weight: 650;
}

.prep-next {
    margin: 0.85rem 0 0.7rem 0;
    padding: 0.75rem 0.9rem;
    border-radius: 12px;
    background: #F3F1FB;
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
    color: var(--ink);
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
    background: var(--navy);
}

.bar-fill-semantic {
    background: var(--accent);
}

.bar-fill-missing {
    background: #C9C4E8;
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
    color: var(--muted);
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
    background: var(--navy);
}

.stack-semantic,
.legend-swatch.stack-semantic {
    background: var(--accent);
}

.stack-missing,
.legend-swatch.stack-missing {
    background: #C9C4E8;
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
    color: var(--ink);
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
    stroke: var(--accent);
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

[data-testid="stSidebar"] .stButton > button {
    width: 100%;
    justify-content: flex-start;
    text-align: left;
    border-radius: 10px;
    min-height: 2.35rem;
}

.profile-identity {
    display: flex;
    gap: 0.9rem;
    align-items: center;
}

.avatar {
    width: 3.1rem;
    height: 3.1rem;
    border-radius: 999px;
    background: var(--navy);
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
    background: #f4f1fb;
    color: var(--navy);
    font-size: 0.82rem;
}

.builder-step.current {
    background: #e4dcff;
    color: #312e81;
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
    background: #F7F8FA;
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
    background: #F3F1FB;
    border-color: #D9D4F2;
}

.completion-filled .completion-icon {
    background: #E4F3EA;
    color: var(--ok);
}

.completion-open .completion-icon {
    background: var(--white);
    border: 1px solid var(--line);
    color: var(--muted);
}

[data-testid="stExpander"] {
    border: 1px solid var(--line) !important;
    border-radius: 12px !important;
    background: var(--white);
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
    grid-template-columns: 1fr;
}

.resume-metric,
.resume-check {
    min-width: 0;
    border: 1px solid var(--line);
    border-radius: 14px;
    background: var(--white);
    padding: 0.8rem 0.85rem 0.75rem 0.85rem;
    box-shadow: var(--shadow);
}

.resume-percent {
    margin: 0.15rem 0;
    color: var(--navy);
    font-size: 1.8rem;
    font-weight: 700;
    letter-spacing: -0.03em;
    line-height: 1.1;
}

.resume-health-label {
    margin: 0.2rem 0 0.35rem 0;
    font-size: 1.45rem;
    font-weight: 700;
    letter-spacing: -0.03em;
    color: #202B45;
}

.resume-health-good { color: #20B8A0; }
.resume-health-mid { color: #6D62C8; }
.resume-health-attention { color: #64748B; }

.resume-note {
    margin: 0.35rem 0 0.8rem 0;
    color: #64748B;
}

.resume-mark {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.15rem;
    height: 1.15rem;
    margin-right: 0.4rem;
    border-radius: 999px;
    background: #EFEDFB;
    color: #6D62C8;
    font-size: 0.72rem;
    font-weight: 700;
    vertical-align: 0.05rem;
}

.resume-found .resume-mark {
    background: #E7F8F4;
    color: #20B8A0;
}

.main:has(.resume-page) [data-testid="stRadio"] [role="radiogroup"] {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
}

.main:has(.resume-page) [data-testid="stRadio"] label {
    margin: 0;
    padding: 0.45rem 0.8rem;
    border: 1px solid #E5E7F0;
    border-radius: 999px;
    background: #FFFFFF;
    color: #202B45;
}

.main:has(.resume-page) [data-testid="stRadio"] label:has(input:checked) {
    background: #EFEDFB;
    border-color: #d9d6f2;
    color: #6D62C8;
}

.resume-metric-value {
    font-size: 1.35rem;
}

.resume-state {
    margin: 0.15rem 0 0.35rem 0;
    color: var(--accent);
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
    background: #FFFFFF !important;
    border: 1px solid #E5E7F0 !important;
    border-radius: 22px !important;
    box-shadow: 0 8px 22px rgba(32, 43, 69, 0.05);
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
    color: #202B45;
}

.main:has(.home-dashboard) [data-testid="stVerticalBlockBorderWrapper"]:has(.home-panel) .match-title,
.main:has(.home-dashboard) [data-testid="stVerticalBlockBorderWrapper"]:has(.home-panel) .home-ring-label {
    color: #202B45;
}

.main:has(.home-dashboard) [data-testid="stVerticalBlockBorderWrapper"]:has(.home-panel) .match-company,
.main:has(.home-dashboard) [data-testid="stVerticalBlockBorderWrapper"]:has(.home-panel) .match-location,
.main:has(.home-dashboard) [data-testid="stVerticalBlockBorderWrapper"]:has(.home-panel) .saved-date,
.main:has(.home-dashboard) [data-testid="stVerticalBlockBorderWrapper"]:has(.home-panel) .hero-lead {
    color: #64748B;
}

.home-match-card,
.home-saved-card {
    min-width: 0;
    margin: 0 0 0.35rem 0;
    padding: 0.85rem 0.9rem 0.75rem 0.9rem;
    border: 1px solid #E5E7F0;
    border-radius: 16px;
    background: #FAFBFF;
    box-shadow: 0 4px 12px rgba(32, 43, 69, 0.04);
    transition: transform 0.16s ease, border-color 0.16s ease, box-shadow 0.16s ease;
}

.home-match-card:hover,
.home-saved-card:hover {
    transform: translateY(-2px);
    border-color: #d9d6f2;
    box-shadow: 0 8px 18px rgba(32, 43, 69, 0.07);
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
    background: #EFEDFB;
    border: 1px solid #E5E7F0;
    color: #6D62C8;
    font-size: 0.78rem;
    font-weight: 700;
}

.home-bookmark {
    flex: 0 0 auto;
    color: #6D62C8;
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
    border-top: 1px solid #E5E7F0;
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
    background: #EFEDFB;
    border: 1px solid #E5E7F0;
    color: #6D62C8;
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
    stroke: #E5E7F0;
}

.home-ring-value {
    stroke: var(--ring, #C4BDE8);
    stroke-linecap: round;
}

.home-ring-high { --ring: #20B8A0; }
.home-ring-mid { --ring: #6D62C8; }
.home-ring-blue { --ring: #3B82F6; }
.home-ring-low { --ring: #C4BDE8; }

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
    border: 1px solid #E5E7F0 !important;
    border-radius: 999px !important;
    background: #EFEDFB !important;
    color: #6D62C8 !important;
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
        font-size: 1.75rem;
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

    .main:has(.home-dashboard) [data-testid="stVerticalBlockBorderWrapper"]:has(.kpi-card)::before {
        aspect-ratio: 1 / 0.92;
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

    .profile-overview-grid {
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
}

@media (max-width: 1180px) {
    .main:has(.home-dashboard) [data-testid="stHorizontalBlock"]:has(.kpi-card) {
        flex-wrap: wrap;
    }

    .main:has(.home-dashboard) [data-testid="stColumn"]:has(.kpi-card) {
        flex: 1 1 calc(50% - 0.8rem) !important;
        min-width: calc(50% - 0.8rem) !important;
        width: auto !important;
    }
}

@media (max-width: 1100px) {
    .main:has(.discover-page) [data-testid="stVerticalBlock"]:has(.discover-grid):not(:has([data-testid="stVerticalBlock"] .discover-grid)) {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .main:has(.discover-page) [data-testid="stVerticalBlockBorderWrapper"]:has(.discover-card)::before {
        aspect-ratio: 1 / 0.96;
    }

    .resume-checks {
        grid-template-columns: 1fr;
    }
}

@media (max-width: 680px) {
    .main:has(.discover-page) [data-testid="stVerticalBlock"]:has(.discover-grid):not(:has([data-testid="stVerticalBlock"] .discover-grid)) {
        grid-template-columns: minmax(0, 1fr);
    }

    .main:has(.discover-page) [data-testid="stVerticalBlockBorderWrapper"]:has(.discover-card)::before {
        display: none;
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

@media (max-width: 560px) {
    .main:has(.home-dashboard) [data-testid="stColumn"]:has(.kpi-card) {
        flex: 1 1 100% !important;
        min-width: 100% !important;
        width: auto !important;
    }

    .main:has(.home-dashboard) [data-testid="stVerticalBlockBorderWrapper"]:has(.kpi-card)::before {
        display: none;
    }
}
</style>
"""


def inject_theme() -> None:
    """Apply the shared colours on every page."""
    st.markdown(CSS, unsafe_allow_html=True)
