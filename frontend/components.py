"""Shared sidebar, cards, and score display."""

import html

import streamlit as st

from auth_session import APP_PAGES, PUBLIC_PAGES, logout
from display import (
    match_quality,
    COUNTRY_NAMES,
    EXPERIENCE_NOT_SPECIFIED,
    INDUSTRY_NOT_SPECIFIED,
    SALARY_NOT_PROVIDED,
    SCORE_UNAVAILABLE,
    SCORE_UNAVAILABLE_REASON,
    WORKPLACE_NOT_SPECIFIED,
    adzuna_attribution,
    employment_label,
    experience_label,
    industry_label,
    job_is_unmatchable,
    jooble_attribution,
    original_listing_link,
    salary_label,
    save_job,
    short_text,
    saved_job_ids,
    workplace_label,
)
from home_metrics import format_score



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
    "Forgot password": ":material/lock_reset:",
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


def _score_number(match: dict, key: str):
    """Return a score the API actually sent. A missing field stays missing."""
    value = match.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def score_bars(match: dict) -> None:
    """Show each returned score against its fixed maximum. Missing parts are omitted."""
    rows = []
    for label, key, maximum in (
        ("Total", "total_score", 100),
        ("Skills", "skill_score", 70),
        ("Role", "role_score", 20),
        ("Location", "location_score", 10),
    ):
        value = _score_number(match, key)
        if value is not None:
            rows.append((label, value, maximum))
    if not rows:
        st.caption("Score details were not returned for this job.")
        return
    st.markdown("<div class='score-breakdown'></div>", unsafe_allow_html=True)
    for label, value, maximum in rows:
        ratio = 0.0 if maximum == 0 else max(0.0, min(float(value) / maximum, 1.0))
        st.markdown(
            (
                "<div class='score-row'>"
                f"<p class='score-label'>{html.escape(label)}</p>"
                f"<p class='score-value'>{html.escape(str(value))}"
                f"<span> / {maximum}</span></p>"
                "</div>"
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
    """Show each related pair with the job skill, the candidate skill, and the returned similarity."""
    blocks = []
    for item in items:
        if not isinstance(item, dict):
            continue
        required = str(item.get("required_skill") or "").strip()
        candidate = str(item.get("candidate_skill") or "").strip()
        similarity = item.get("similarity")
        if not required or not candidate or isinstance(similarity, bool) or not isinstance(similarity, (int, float)):
            continue
        percent = f"{float(similarity) * 100:.2f}%"
        phrase = f"{required} · your skill {candidate} · {percent}"
        blocks.append(
            "<div class='skill-pair'>"
            f"<p class='detail-line'><span>Job requires</span> {html.escape(required)}</p>"
            f"<p class='detail-line'><span>Your skill</span> {html.escape(candidate)}</p>"
            f"<p class='detail-line'><span>Similarity</span> {html.escape(percent)}</p>"
            f"<p class='skill-pair-phrase'>{html.escape(phrase)}</p>"
            "</div>"
        )
    if blocks:
        st.markdown("".join(blocks), unsafe_allow_html=True)


def _match_facts(job: dict) -> str:
    """List only job facts the payload actually includes."""
    lines = []
    country_code = str(job.get("source_country") or "").strip().casefold()
    if country_code:
        country = COUNTRY_NAMES.get(country_code, country_code.upper())
        lines.append(f"Country: {country}")
    source = " ".join(str(job.get("source") or "").split())
    if source and source.casefold() not in {"adzuna", "jooble"}:
        lines.append(f"Source: {source}")
    industry = industry_label(job)
    if industry != INDUSTRY_NOT_SPECIFIED:
        lines.append(f"Industry: {industry}")
    experience = experience_label(job)
    if experience != EXPERIENCE_NOT_SPECIFIED:
        lines.append(experience)
    employment = employment_label(job)
    if employment:
        lines.append(f"Employment type: {employment}")
    salary = salary_label(job)
    if salary != SALARY_NOT_PROVIDED:
        lines.append(salary)
    workplace = workplace_label(job)
    if workplace != WORKPLACE_NOT_SPECIFIED:
        lines.append(workplace)
    posted = " ".join(str(job.get("posted_at") or "").split())
    if posted and posted.casefold() != "none":
        lines.append(f"Posted: {posted.replace('T', ' ')[:16]}")
    if not lines:
        return ""
    return f"<p class='detail-line match-meta'>{html.escape(' · '.join(lines))}</p>"


def _parts_add_up(match: dict) -> str:
    """Say whether the returned parts equal the returned total. Do not replace either."""
    numbers = [_score_number(match, key) for key in ("skill_score", "role_score", "location_score")]
    total = _score_number(match, "total_score")
    if total is None or any(value is None for value in numbers):
        return ""
    if abs(sum(float(value) for value in numbers) - float(total)) > 0.02:
        return "<p class='form-hint'>The overall score shown is the total returned for this job.</p>"
    return "<p class='form-hint'>Skills, role, and location add up to the overall score.</p>"


def _open_preparation(job_id) -> None:
    """Open the existing preparation journal for one stored job."""
    st.session_state.selected_job_id = job_id
    st.session_state.nav = "Discover Jobs"


def render_match_card(match: dict) -> None:
    """One ranked job, including the returned score, skills, explanation, and actions."""
    job = match.get("job") if isinstance(match.get("job"), dict) else {}
    title = html.escape(str(job.get("title") or "Untitled role"))
    company = html.escape(str(job.get("company") or "Company not provided"))
    location = html.escape(str(job.get("location") or "Location not provided"))
    total = _score_number(match, "total_score")
    if total is None:
        score = "<p class='hero-lead match-score'>No overall score was returned for this job.</p>"
    else:
        score = (
            f"<p class='score-hero match-score'>{html.escape(format_score(total))}</p>"
            f"<p class='hero-lead'>{html.escape(match_quality(total))}</p>"
        )
    snippet = ""
    if job.get("description_is_snippet"):
        text = " ".join(str(job.get("description") or "").split())
        snippet = "<p class='form-hint'>The provider supplied a description snippet, not the full advertisement.</p>"
        if text:
            snippet += f"<p class='detail-line'>{html.escape(short_text(text, 180))}</p>"
    with st.container(border=True):
        st.markdown("<div class='match-overview match-report'></div>", unsafe_allow_html=True)
        copy_col, score_col = st.columns([1.25, 0.85], gap="large")
        with copy_col:
            st.markdown(
                (
                    f"<h3 class='match-title match-card'>{title}</h3>"
                    f"<p class='match-company'>{company}</p>"
                    f"<p class='match-location'>{location}</p>"
                    f"{_match_facts(job)}"
                ),
                unsafe_allow_html=True,
            )
            credit = adzuna_attribution(job) + jooble_attribution(job) + original_listing_link(job)
            if credit:
                st.markdown(f"<div class='discover-sources'>{credit}</div>", unsafe_allow_html=True)
            if snippet:
                st.markdown(snippet, unsafe_allow_html=True)
        with score_col:
            st.markdown(
                (
                    "<p class='section-label'>Overall match</p>"
                    f"{score}"
                    "<p class='form-hint'>Skills can contribute 70, preferred role 20, "
                    "and preferred location 10. This text does not calculate the score.</p>"
                    f"{_parts_add_up(match)}"
                ),
                unsafe_allow_html=True,
            )
        score_bars(match)
        _render_skill_comparison(match)
        _render_match_explanation(match)
        _render_match_actions(job)


def _render_skill_comparison(match: dict) -> None:
    """Group the skill lists returned for this job. Empty groups stay one short line."""
    exact = [str(skill) for skill in (match.get("matched_skills") or []) if str(skill).strip()]
    semantic_matches = [item for item in (match.get("semantic_matches") or []) if isinstance(item, dict)]
    missing = [str(skill) for skill in (match.get("missing_skills") or []) if str(skill).strip()]
    extra = [str(skill) for skill in (match.get("unused_candidate_skills") or []) if str(skill).strip()]
    st.markdown("<p class='section-label'>Skills comparison</p>", unsafe_allow_html=True)
    exact_col, related_col, missing_col = st.columns(3, gap="medium")
    with exact_col:
        st.markdown("<p class='skill-heading'>Exact matches</p>", unsafe_allow_html=True)
        if exact:
            chips(exact, "exact")
        else:
            st.markdown("<p class='hero-lead'>No exact skill matches were returned.</p>", unsafe_allow_html=True)
    with related_col:
        st.markdown("<p class='skill-heading'>Semantic matches</p>", unsafe_allow_html=True)
        if semantic_matches:
            semantic_chips(semantic_matches)
        else:
            st.markdown("<p class='hero-lead'>No related skill matches were returned.</p>", unsafe_allow_html=True)
    with missing_col:
        st.markdown("<p class='skill-heading'>Missing skills</p>", unsafe_allow_html=True)
        if missing:
            chips(missing, "missing")
            names = ", ".join(html.escape(skill) for skill in missing)
            st.markdown(
                f"<p class='hero-lead'>These required skills are not matched yet: {names}.</p>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<p class='hero-lead'>Every listed required skill is matched.</p>",
                unsafe_allow_html=True,
            )
    if extra:
        st.markdown("<p class='skill-heading'>Other profile skills</p>", unsafe_allow_html=True)
        st.markdown(
            "<p class='form-hint'>Profile skills returned as not required by this job.</p>",
            unsafe_allow_html=True,
        )
        chips(extra, "semantic")


def _render_match_explanation(match: dict) -> None:
    """Show the returned explanation without rewriting its facts."""
    explanation = str(match.get("explanation") or "").strip()
    if not explanation:
        explanation = "No explanation was returned for this job."
    st.markdown(
        (
            "<p class='section-label'>Why this job matches</p>"
            "<p class='form-hint'>This explanation was returned with the match. "
            "It does not calculate or change the score.</p>"
            f"<div class='insight-panel match-explanation'>{html.escape(explanation)}</div>"
        ),
        unsafe_allow_html=True,
    )


def _render_match_actions(job: dict) -> None:
    """Keep save, the original listing, and preparation on the paths that already exist."""
    job_id = job.get("id")
    live = str(job.get("source") or "").casefold() == "jooble" or not isinstance(job_id, int)
    st.markdown("<div class='match-actions'></div>", unsafe_allow_html=True)
    if live:
        action_col, discover_col = st.columns(2)
        with action_col:
            st.caption("Live results are not stored.")
        with discover_col:
            st.button("Discover Jobs", key=f"match-discover-{job_id}", on_click=select_page, args=("Discover Jobs",))
        return
    action_col, prep_col, discover_col = st.columns(3)
    with action_col:
        if job_id in saved_job_ids(st.session_state.get("saved_jobs")):
            st.button("Saved", key=f"saved-state-{job_id}", disabled=True)
        elif st.button("Save Job", key=f"save-{job_id}", type="primary"):
            save_job(job)
    with prep_col:
        st.button("Open preparation", key=f"match-prep-{job_id}", on_click=_open_preparation, args=(job_id,))
    with discover_col:
        st.button("Discover Jobs", key=f"match-discover-{job_id}", on_click=select_page, args=("Discover Jobs",))


def _saved_place(job: dict) -> str:
    """Location and country when the saved listing actually includes them."""
    location = " ".join(str(job.get("location") or "").split())
    country_code = str(job.get("source_country") or "").strip().casefold()
    country = COUNTRY_NAMES.get(country_code, country_code.upper())
    if country and country.casefold() not in location.casefold():
        location = f"{location} · {country}" if location else country
    return html.escape(location)


def _saved_meta_html(job: dict) -> str:
    """Listing facts that were stored. Missing salary, experience, and type stay off the card."""
    lines = []
    industry = industry_label(job)
    if industry != INDUSTRY_NOT_SPECIFIED:
        lines.append(f"Industry: {industry}")
    experience = experience_label(job)
    if experience != EXPERIENCE_NOT_SPECIFIED:
        lines.append(experience)
    employment = employment_label(job)
    if employment:
        lines.append(f"Employment type: {employment}")
    salary = salary_label(job)
    if salary != SALARY_NOT_PROVIDED:
        lines.append(salary)
    workplace = workplace_label(job)
    if workplace != WORKPLACE_NOT_SPECIFIED:
        lines.append(workplace)
    return "".join(f"<p class='detail-line discover-meta'>{html.escape(line)}</p>" for line in lines)


def _saved_score_html(job: dict, match) -> str:
    """Show a returned score, or say that this listing cannot be scored."""
    if job_is_unmatchable(job):
        reason = " ".join(str(job.get("matchability_reason") or "").split())
        explanation = reason or SCORE_UNAVAILABLE_REASON
        return (
            "<p class='hero-lead discover-score saved-footer'>"
            f"{html.escape(SCORE_UNAVAILABLE)}</p>"
            f"<p class='hero-lead saved-reason'>{html.escape(explanation)}</p>"
        )
    if isinstance(match, dict) and match.get("total_score") is not None:
        shown = html.escape(format_score(match["total_score"]))
        quality = html.escape(match_quality(float(match["total_score"])))
        return (
            "<p class='score-value discover-score saved-footer'>"
            f"Match {shown}</p>"
            f"<p class='hero-lead saved-quality'>{quality}</p>"
        )
    return "<p class='hero-lead discover-score saved-footer'>Not ranked yet</p>"


def render_saved_card(item: dict, match=None, on_open=None, on_match=None) -> None:
    """One saved job. The full description and preparation notes stay behind View details."""
    job = item.get("job") or {}
    saved_at = str(item.get("created_at") or "").replace("T", " ")[:16]
    title = html.escape(job.get("title") or "Untitled role")
    company = html.escape(" ".join(str(job.get("company") or "").split()))
    location = _saved_place(job)
    badge = adzuna_attribution(job) or jooble_attribution(job)
    badge_html = f"<div class='discover-badge'>{badge}</div>" if badge else ""
    company_html = f"<p class='match-company'>{company}</p>" if company else ""
    location_html = f"<p class='match-location'>{location}</p>" if location else ""
    saved_html = f"<p class='saved-date'>Saved {html.escape(saved_at)}</p>" if saved_at else ""
    with st.container(border=True):
        st.markdown(
            (
                "<div class='saved-card-body'>"
                f"{badge_html}"
                f"<h3 class='match-title saved-card discover-card'>{title}</h3>"
                f"{company_html}"
                f"{location_html}"
                f"{_saved_meta_html(job)}"
                f"{saved_html}"
                f"{_saved_score_html(job, match)}"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        link = original_listing_link(job)
        st.markdown(
            f"<div class='saved-actions discover-actions'>{link}</div>",
            unsafe_allow_html=True,
        )
        if on_open is not None and job.get("id") is not None:
            st.button(
                "View details",
                key=f"saved-detail-{item.get('id')}",
                on_click=on_open,
                args=(job.get("id"),),
            )
        if (
            on_match is not None
            and isinstance(job.get("id"), int)
            and isinstance(match, dict)
            and match.get("total_score") is not None
            and not job_is_unmatchable(job)
        ):
            st.button(
                "View match",
                key=f"saved-match-{item.get('id')}",
                on_click=on_match,
                args=(job.get("id"),),
            )
