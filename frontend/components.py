"""Shared sidebar, cards, and score display."""

import html

import streamlit as st

from auth_session import APP_PAGES, PUBLIC_PAGES, logout
from display import (
    adzuna_attribution,
    job_is_unmatchable,
    listing_notes_html,
    original_listing_link,
    real_skills,
    save_job,
    short_text,
    unavailable_score_html,
)
from home_metrics import format_score
from preparation import limited_skills



def select_page(page_name: str) -> None:
    """Store the chosen page before the sidebar menu is drawn."""
    st.session_state.nav = page_name


def page_header(title: str, subtitle: str, eyebrow: str = "") -> None:
    """Show a page title and a short line of description beneath it."""
    if eyebrow:
        st.markdown(
            f"<p class='eyebrow page-eyebrow'>{html.escape(eyebrow)}</p>",
            unsafe_allow_html=True,
        )
    st.title(title)
    st.markdown(f"<p class='page-subtitle'>{html.escape(subtitle)}</p>", unsafe_allow_html=True)


def empty_state(title: str, body: str, marker: str) -> None:
    """Quiet empty panel. The marker class keeps the card spacing consistent."""
    st.markdown(
        (
            f"<p class='section-label {marker}'>{html.escape(title)}</p>"
            f"<p class='hero-lead'>{html.escape(body)}</p>"
        ),
        unsafe_allow_html=True,
    )


def section_label(text: str) -> None:
    """Label one block inside a card."""
    st.markdown(f"<p class='section-label'>{html.escape(text)}</p>", unsafe_allow_html=True)


_NAV_ICONS = {
    "Home": ":material/home:",
    "My Profile": ":material/person:",
    "Discover Jobs": ":material/search:",
    "Match Insights": ":material/insights:",
    "Saved Jobs": ":material/bookmark:",
    "Resume Centre": ":material/description:",
    "Login": ":material/login:",
    "Sign Up": ":material/person_add:",
    "Account setup": ":material/key:",
}


def render_sidebar(api_ok: bool) -> str:
    """Show one navigation list and return the page chosen for this visit."""
    logged_in = bool(st.session_state.get("auth_token") and st.session_state.get("candidate_id"))
    pages = APP_PAGES if logged_in else PUBLIC_PAGES
    if st.session_state.get("nav") not in pages:
        st.session_state.nav = "Home" if logged_in else "Login"
    st.sidebar.markdown(
        """
        <div class="sidebar-brand">
            <div class="sidebar-mark">AJ</div>
            <div>
                <p class="sidebar-title">AI Job Matching</p>
                <p class="sidebar-tag">Recruitment Workspace</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    page = st.session_state.nav
    for name in pages:
        st.sidebar.button(
            name,
            icon=_NAV_ICONS[name],
            on_click=select_page,
            args=(name,),
            key=f"nav-{name}",
            type="primary" if name == page else "secondary",
            width="stretch",
        )
    if logged_in:
        st.sidebar.button("Log out", icon=":material/logout:", on_click=logout, key="logout", width="stretch")

    profile = st.session_state.get("profile")
    profile = profile if isinstance(profile, dict) else {}
    if not logged_in:
        name = "Not signed in"
        detail = "Log in to continue."
    else:
        name = html.escape(str(profile.get("name") or st.session_state.get("candidate_name") or "Signed in"))
        detail = str(profile.get("email") or "Signed in")
    status = "API is running" if api_ok else "API is not reachable"
    status_class = "status-ok" if api_ok else "status-down"
    st.sidebar.markdown(
        f"""
        <div class="sidebar-session">
            <p class="sidebar-kicker">Session</p>
            <p class="sidebar-name">{name}</p>
            <p class="sidebar-meta">{html.escape(detail)}</p>
            <p class="sidebar-meta"><span class="status-dot {status_class}"></span>{status}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return page


def require_profile() -> bool:
    """Stop a page when this session has not saved a profile."""
    if st.session_state.candidate_id is None:
        with st.container(border=True):
            empty_state(
                "Profile needed",
                "Save a profile on My Profile first. Match Insights and Saved Jobs stay closed until then.",
                "gate-card",
            )
            st.button("Go to My Profile", on_click=select_page, args=("My Profile",), type="primary")
        return False
    signed_in_as = html.escape(str(st.session_state.candidate_name or "your account"))
    st.markdown(
        f"<p class='status-line profile-context'>Signed in as {signed_in_as}</p>",
        unsafe_allow_html=True,
    )
    return True


def score_bars(match: dict) -> None:
    """Show the four scores as separate indicators on a match card."""
    rows = [
        ("Total", match["total_score"], 100),
        ("Skills", match["skill_score"], 70),
        ("Role", match["role_score"], 20),
        ("Location", match["location_score"], 10),
    ]
    columns = st.columns(4, gap="small")
    for column, (label, value, maximum) in zip(columns, rows):
        ratio = 0.0 if maximum == 0 else max(0.0, min(float(value) / maximum, 1.0))
        with column:
            st.markdown(
                (
                    f"<p class='score-label'>{html.escape(label)}</p>"
                    f"<p class='score-value'>{html.escape(str(value))}"
                    f"<span> / {maximum}</span></p>"
                ),
                unsafe_allow_html=True,
            )
            st.progress(ratio, text=f"{label} {value} / {maximum}")


def chips(labels: list[str], kind: str) -> None:
    """Draw skill labels. An empty list stays a plain None, not an empty chip row."""
    if not labels:
        st.caption("None")
        return
    pieces = [
        f'<span class="chip chip-{kind}">{html.escape(label)}</span>'
        for label in labels
        if isinstance(label, str) and label.strip()
    ]
    if not pieces:
        st.caption("None")
        return
    st.markdown(f'<div class="chip-row">{"".join(pieces)}</div>', unsafe_allow_html=True)


def render_profile_summary(profile: dict) -> None:
    """Show the profile fields returned by the API."""
    name = html.escape(str(profile.get("name") or ""))
    email = html.escape(str(profile.get("email") or ""))
    education = html.escape(str(profile.get("education") or "Not provided"))
    years = html.escape(str(profile.get("years_experience", 0)))
    with st.container(border=True):
        st.markdown(
            (
                "<p class='section-label profile-summary'>Saved profile</p>"
                f"<h3 class='match-title'>{name}</h3>"
                f"<p class='match-company'>{email}</p>"
            ),
            unsafe_allow_html=True,
        )
        section_label("Background")
        st.markdown(
            (
                f"<p class='detail-line'>Education: {education}</p>"
                f"<p class='detail-line'>Years of experience: {years}</p>"
            ),
            unsafe_allow_html=True,
        )
        section_label("Skills")
        chips(profile.get("skills") or [], "exact")
        section_label("Preferences")
        st.markdown("<p class='skill-heading'>Preferred roles</p>", unsafe_allow_html=True)
        chips(profile.get("preferred_roles") or [], "semantic")
        st.markdown("<p class='skill-heading'>Preferred locations</p>", unsafe_allow_html=True)
        chips(profile.get("preferred_locations") or [], "semantic")


def semantic_chips(items: list[dict]) -> None:
    """Lavender chips for related skills, each with its similarity percentage."""
    pieces = []
    for item in items:
        percent = f"{float(item['similarity']) * 100:.2f}%"
        label = (
            f"{item['required_skill']} · your skill {item['candidate_skill']} · {percent}"
        )
        pieces.append(f'<span class="chip chip-semantic">{html.escape(label)}</span>')
    if pieces:
        st.markdown(f'<div class="chip-row">{"".join(pieces)}</div>', unsafe_allow_html=True)


def render_match_card(match: dict) -> None:
    """One ranked job, including exact skills, semantic pairs, and Save Job."""
    job = match["job"]
    with st.container(border=True):
        st.markdown(
            (
                f"<h3 class='match-title match-card'>{html.escape(str(job['title']))}</h3>"
                f"<p class='match-company'>{html.escape(str(job['company']))}</p>"
                f"<p class='match-location'>{html.escape(str(job.get('location') or ''))}</p>"
            ),
            unsafe_allow_html=True,
        )
        section_label("Scores")
        score_bars(match)
        section_label("Skills breakdown")
        st.markdown("<p class='skill-heading'>Exact matches</p>", unsafe_allow_html=True)
        chips(match.get("matched_skills") or [], "exact")
        semantic_matches = match.get("semantic_matches") or []
        if semantic_matches:
            st.markdown("<p class='skill-heading'>Semantic matches</p>", unsafe_allow_html=True)
            semantic_chips(semantic_matches)
        st.markdown("<p class='skill-heading'>Missing skills</p>", unsafe_allow_html=True)
        chips(match.get("missing_skills") or [], "missing")
        section_label("Explanation")
        explanation = str(match.get("explanation") or "").strip()
        if not explanation:
            explanation = "No explanation was returned for this job."
        st.markdown(f"<div class='insight-panel'>{html.escape(explanation)}</div>", unsafe_allow_html=True)
        if st.button("Save Job", key=f"save-{job['id']}", type="primary"):
            save_job(job)


def render_saved_card(item: dict, match=None, on_open=None) -> None:
    """One saved job in the grid. Full text stays in View details."""
    job = item.get("job") or {}
    saved_at = str(item.get("created_at") or "").replace("T", " ")[:16]
    title = html.escape(short_text(job.get("title") or "Untitled role", 72))
    company = html.escape(short_text(job.get("company") or "", 48))
    location = html.escape(short_text(job.get("location") or "", 48))
    description = " ".join(str(job.get("description") or "").split())
    blurb = short_text(description, 140) if description else ""
    if job_is_unmatchable(job):
        score = unavailable_score_html("discover-score saved-footer")
    elif isinstance(match, dict) and match.get("total_score") is not None:
        score = (
            "<p class='score-value discover-score saved-footer'>"
            f"Match {html.escape(format_score(match['total_score']))}</p>"
        )
    else:
        score = "<p class='hero-lead discover-score saved-footer'>Not ranked yet</p>"
    with st.container(border=True):
        st.markdown(
            (
                f"<h3 class='match-title saved-card discover-card'>{title}</h3>"
                f"<p class='match-company'>{company}</p>"
                f"<p class='match-location'>{location}</p>"
                f"<p class='saved-date'>Saved {html.escape(saved_at)}</p>"
                + (f"<div class='insight-panel'>{html.escape(blurb)}</div>" if blurb else "")
                + listing_notes_html(job)
            ),
            unsafe_allow_html=True,
        )
        shown, extra = limited_skills(real_skills(job))
        if shown:
            chips(shown, "exact")
        if extra:
            st.markdown(
                f"<p class='discover-more'>+{extra} more in details</p>",
                unsafe_allow_html=True,
            )
        st.markdown(score, unsafe_allow_html=True)
        credit = adzuna_attribution(job)
        listing = original_listing_link(job)
        if credit or listing:
            st.markdown(credit + listing, unsafe_allow_html=True)
        if on_open is not None and job.get("id") is not None:
            st.button(
                "View details",
                key=f"saved-detail-{item.get('id')}",
                on_click=on_open,
                args=(job.get("id"),),
            )
