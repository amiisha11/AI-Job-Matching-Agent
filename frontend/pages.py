"""The five sidebar pages. Each one reads the signed-in candidate's API data."""

import html
from urllib.parse import urlencode

import streamlit as st

from auth_pages import render_change_password
from auth_session import authed_request
from home_metrics import (
    average_match_score,
    format_score,
    recent_saved,
    format_share,
    score_distribution,
    skill_breakdown,
    skill_shares,
    top_matches,
)
from components import (
    chips,
    empty_state,
    page_header,
    render_match_card,
    render_saved_card,
    require_profile,
    select_page,
)
from display import (
    COUNTRY_NAMES,
    adzuna_attribution,
    jooble_attribution,
    omit_repeated_jobs,
    initials,
    job_heading,
    job_is_unmatchable,
    job_key,
    listing_notes_html,
    match_quality,
    matches_by_job,
    real_skills,
    original_listing_link,
    rankable_matches,
    save_job,
    saved_job_ids,
    short_text,
    unavailable_score_html,
)
from preparation import limited_skills, progress_lines
from profile_metrics import (
    COMPLETION_EXPLANATION,
    SKILL_NOTE,
    completion_percent,
    experience_text,
    filled_section_count,
    profile_sections,
    section_suggestions,
)
from profile_builder import (
    DEGREE_OPTIONS,
    EDUCATION_OPTIONS,
    EXPERIENCE_YEARS,
    FIELD_OPTIONS,
    LOCATION_OPTIONS,
    REMOTE_OPTIONS,
    ROLE_OPTIONS,
    SKILL_OPTIONS,
    include_custom,
    profile_payload,
)


def page_home(status: dict | None, status_error: str | None) -> None:
    """Dashboard for the signed-in candidate. Figures come from the API cache in this session."""
    st.markdown("<div class='home-dashboard'></div>", unsafe_allow_html=True)
    jobs_error, saved_error, match_error = _load_home_data()
    if status_error:
        status_line = "The local API is not reachable."
    elif isinstance(status, dict):
        status_line = str(status.get("message") or "API is running.")
    else:
        status_line = "API is running."
    profile = st.session_state.get("profile") or {}
    name = str(profile.get("name") or st.session_state.get("candidate_name") or "there")
    page_header(
        f"Hello, {name}",
        "A snapshot of the jobs available to you, how they score, and what you have saved.",
        "Dashboard",
    )
    st.markdown(
        "<p class='home-note'>Every opportunity you explore brings you one step closer to your goals.</p>",
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        st.markdown(
            (
                "<p class='eyebrow home-hero'>Welcome</p>"
                "<p class='hero-lead'>Open a job list, review the ranking, or update the profile behind these numbers.</p>"
                f"<p class='status-line'>{html.escape(status_line)}</p>"
            ),
            unsafe_allow_html=True,
        )
        discover_col, insights_col, profile_col = st.columns(3, gap="large")
        with discover_col:
            st.button("Discover Jobs", on_click=select_page, args=("Discover Jobs",))
        with insights_col:
            st.button("Match Insights", on_click=select_page, args=("Match Insights",), type="primary")
        with profile_col:
            st.button("My Profile", on_click=select_page, args=("My Profile",))

    jobs = st.session_state.get("job_catalog")
    matches = st.session_state.get("matches")
    saved_jobs = st.session_state.get("saved_jobs")
    _render_kpis(jobs, jobs_error, matches, match_error, saved_jobs, saved_error)
    for message in (jobs_error, saved_error, match_error):
        if message:
            st.error(message)
    distribution_col, skill_col = st.columns(2, gap="large")
    with distribution_col:
        _render_distribution(matches, match_error)
    with skill_col:
        _render_skill_chart(matches, match_error)
    st.markdown(
        "<p class='home-note home-note-soft'>Small improvements today can create big opportunities tomorrow.</p>",
        unsafe_allow_html=True,
    )
    match_col, saved_col = st.columns(2, gap="large")
    with match_col:
        _render_recent_matches(matches, match_error)
    with saved_col:
        _render_recent_saved(saved_jobs, saved_error)


def _load_home_data() -> tuple[str | None, str | None, str | None]:
    """Fetch each dashboard source once, then reuse the session copy."""
    jobs_error = None
    saved_error = None
    match_error = None
    candidate_id = st.session_state.candidate_id
    pending = (
        st.session_state.get("job_catalog") is None
        or st.session_state.get("saved_jobs") is None
        or st.session_state.get("matches") is None
    )
    if not pending:
        return None, None, None
    with st.spinner("Loading your dashboard. Ranking can take a moment the first time."):
        if st.session_state.get("job_catalog") is None:
            jobs, jobs_error = authed_request("GET", "/jobs/")
            if jobs_error is None and isinstance(jobs, list):
                st.session_state.job_catalog = jobs
            else:
                jobs_error = jobs_error or "The job list could not be read."
        if st.session_state.get("saved_jobs") is None:
            saved, saved_error = authed_request("GET", f"/candidates/{candidate_id}/saved-jobs")
            if saved_error is None and isinstance(saved, list):
                st.session_state.saved_jobs = saved
            else:
                saved_error = saved_error or "Saved jobs could not be read."
        if st.session_state.get("matches") is None:
            found, match_error = authed_request(
                "GET",
                f"/candidates/{candidate_id}/matches",
                timeout=60,
            )
            if match_error is None and isinstance(found, list):
                st.session_state.matches = rankable_matches(found)
            else:
                match_error = match_error or "Match scores could not be read."
    return jobs_error, saved_error, match_error


def _render_kpis(jobs, jobs_error, matches, match_error, saved_jobs, saved_error) -> None:
    """Four figures. A failed request stays a dash instead of an invented zero."""
    total_jobs = "—" if jobs_error or not isinstance(jobs, list) else str(len(jobs))
    if match_error or not isinstance(matches, list):
        matched = "—"
        average = "—"
    else:
        matched = str(len(matches))
        mean = average_match_score(matches)
        average = "—" if mean is None else format_score(mean)
    saved_count = "—" if saved_error or not isinstance(saved_jobs, list) else str(len(saved_jobs))
    cards = (
        ("Total jobs", total_jobs, "Listings stored for matching", _KPI_ICONS["jobs"]),
        ("Jobs matched", matched, "Jobs scored for your profile", _KPI_ICONS["matched"]),
        ("Saved jobs", saved_count, "Roles you kept", _KPI_ICONS["saved"]),
        ("Average match score", average, "Mean score of the ranked jobs", _KPI_ICONS["score"]),
    )
    columns = st.columns(4, gap="medium")
    for column, (label, value, note, icon) in zip(columns, cards):
        with column:
            with st.container(border=True):
                st.markdown(
                    (
                        f"<span class='kpi-icon' aria-hidden='true'>{icon}</span>"
                        f"<p class='section-label kpi-card'>{html.escape(label)}</p>"
                        f"<p class='kpi-value'>{html.escape(value)}</p>"
                        f"<p class='hero-lead'>{html.escape(note)}</p>"
                    ),
                    unsafe_allow_html=True,
                )


_KPI_ICONS = {
    "jobs": (
        "<svg viewBox='0 0 24 24'><rect x='4' y='7' width='16' height='12' rx='2'></rect>"
        "<path d='M9 7V5.5A1.5 1.5 0 0 1 10.5 4h3A1.5 1.5 0 0 1 15 5.5V7'></path></svg>"
    ),
    "matched": (
        "<svg viewBox='0 0 24 24'><circle cx='12' cy='12' r='7'></circle>"
        "<circle cx='12' cy='12' r='3'></circle></svg>"
    ),
    "saved": (
        "<svg viewBox='0 0 24 24'><path d='M7 4h10a1 1 0 0 1 1 1v15l-6-3.2L6 20V5a1 1 0 0 1 1-1z'></path></svg>"
    ),
    "score": (
        "<svg viewBox='0 0 24 24'><path d='M5 16l4-4 3 3 7-7'></path>"
        "<path d='M14 8h5v5'></path></svg>"
    ),
}


def _score_chart(rows: list[tuple[str, int]]) -> str:
    """Column chart on one scale. A zero range keeps its label and its count."""
    peak = max((count for _, count in rows), default=0)
    columns = []
    for label, count in rows:
        height = 0 if peak == 0 else (100 * count / peak)
        columns.append(
            "<div class='score-column'>"
            f"<span class='column-label'>{html.escape(label)}</span>"
            f"<span class='column-value'>{count}</span>"
            "<span class='column-track'>"
            f"<span class='column-bar' style='height: {height:.1f}%'></span>"
            "</span></div>"
        )
    return (
        "<p class='chart-caption'>Number of ranked jobs in each score range.</p>"
        "<div class='score-chart'>"
        f"<span class='scale-max'>{peak}</span>"
        "<div class='score-plot'>"
        "<span class='gridline gridline-top'></span>"
        "<span class='gridline gridline-mid'></span>"
        f"{''.join(columns)}"
        "</div></div>"
    )


def _skill_chart(breakdown: dict[str, int]) -> str:
    """One stacked bar. Each percentage is that count divided by every skill comparison."""
    shares = skill_shares(breakdown)
    classes = {
        "Exact matches": "stack-exact",
        "Semantic matches": "stack-semantic",
        "Missing skills": "stack-missing",
    }
    segments = []
    legend = []
    for label, count, share in shares:
        kind = classes[label]
        if share:
            segments.append(
                f"<span class='stack-segment {kind}' style='width: {share:.1f}%'></span>"
            )
        legend.append(
            "<li class='legend-item'>"
            f"<span class='legend-swatch {kind}'></span>"
            f"<span class='legend-label'>{html.escape(label)}</span>"
            f"<span class='legend-count'>{count}</span>"
            f"<span class='legend-share'>{html.escape(format_share(share))}</span>"
            "</li>"
        )
    return (
        "<p class='chart-caption'>Skill comparisons across the ranked jobs, not a share of jobs.</p>"
        f"<div class='stacked-bar'>{''.join(segments)}</div>"
        f"<ul class='chart-legend'>{''.join(legend)}</ul>"
    )


def _render_distribution(matches, match_error) -> None:
    with st.container(border=True):
        st.markdown(
            "<p class='section-label chart-card'>Match score distribution</p>",
            unsafe_allow_html=True,
        )
        if match_error or not isinstance(matches, list):
            st.markdown(
                "<p class='hero-lead chart-unavailable'>Score ranges appear after the ranking request succeeds.</p>",
                unsafe_allow_html=True,
            )
            return
        if not matches:
            st.markdown(
                "<p class='hero-lead chart-unavailable'>No jobs have been scored yet.</p>",
                unsafe_allow_html=True,
            )
            return
        st.markdown(_score_chart(score_distribution(matches)), unsafe_allow_html=True)


def _render_skill_chart(matches, match_error) -> None:
    with st.container(border=True):
        st.markdown(
            (
                "<p class='section-label chart-card'>Skill match breakdown</p>"
                "<p class='home-note'>Your next opportunity might be one skill away. Keep learning.</p>"
            ),
            unsafe_allow_html=True,
        )
        if match_error or not isinstance(matches, list):
            st.markdown(
                "<p class='hero-lead chart-unavailable'>Skill counts appear after the ranking request succeeds.</p>",
                unsafe_allow_html=True,
            )
            return
        if not matches:
            st.markdown(
                "<p class='hero-lead chart-unavailable'>No jobs have been scored yet.</p>",
                unsafe_allow_html=True,
            )
            return
        st.markdown(_skill_chart(skill_breakdown(matches)), unsafe_allow_html=True)


def _render_recent_matches(matches, match_error) -> None:
    with st.container(border=True):
        st.markdown("<p class='section-label home-recent home-panel'>Recent matches</p>", unsafe_allow_html=True)
        if match_error or not isinstance(matches, list):
            st.markdown(
                "<p class='hero-lead chart-unavailable'>Recent matches appear after the ranking request succeeds.</p>",
                unsafe_allow_html=True,
            )
            return
        chosen = top_matches(matches)
        if not chosen:
            st.markdown(
                "<p class='hero-lead chart-unavailable'>No scored jobs to show yet.</p>",
                unsafe_allow_html=True,
            )
            return
        for match in chosen:
            st.markdown(_match_preview(match), unsafe_allow_html=True)
            job = match["job"]
            st.button(
                "View match",
                key=f"home-match-{job.get('id')}",
                on_click=_open_match,
                args=(job.get("id"),),
            )


def _open_match(job_id) -> None:
    """Open Match Insights on the job the candidate chose."""
    st.session_state.selected_match_id = job_id
    st.session_state.nav = "Match Insights"


def _render_recent_saved(saved_jobs, saved_error) -> None:
    with st.container(border=True):
        st.markdown("<p class='section-label home-saved home-panel'>Recently saved jobs</p>", unsafe_allow_html=True)
        if saved_error or not isinstance(saved_jobs, list):
            st.markdown(
                "<p class='hero-lead chart-unavailable'>Saved jobs appear after that request succeeds.</p>",
                unsafe_allow_html=True,
            )
            return
        chosen = recent_saved(saved_jobs)
        if not chosen:
            st.markdown(
                "<p class='hero-lead chart-unavailable'>You have not saved any jobs yet.</p>",
                unsafe_allow_html=True,
            )
            return
        for item in chosen:
            st.markdown(_saved_preview(item), unsafe_allow_html=True)
        st.button("View all", on_click=select_page, args=("Saved Jobs",), key="home-view-saved")


def _ring_tone(score: float) -> str:
    """Color band for a real score. The number itself is not changed."""
    value = float(score)
    if value >= 80:
        return "high"
    if value >= 60:
        return "mid"
    if value >= 40:
        return "blue"
    return "low"


def _score_ring(score) -> str:
    """Circular indicator for one API score."""
    value = max(0.0, min(float(score), 100.0))
    radius = 26
    length = 2 * 3.141592653589793 * radius
    offset = length * (1 - value / 100)
    shown = html.escape(format_score(score))
    return (
        f"<div class='home-ring home-ring-{_ring_tone(value)}'>"
        "<svg viewBox='0 0 72 72' aria-hidden='true'>"
        "<circle class='home-ring-track' cx='36' cy='36' r='26'></circle>"
        "<circle class='home-ring-value' cx='36' cy='36' r='26' "
        f"stroke-dasharray='{length:.2f}' stroke-dashoffset='{offset:.2f}'></circle>"
        "</svg>"
        f"<span class='home-ring-label'>{shown}</span>"
        f"<span class='home-score-text'>Score {shown}</span>"
        "</div>"
    )


def _match_highlights(match: dict) -> list[str]:
    """Skills the ranking actually matched. Missing skills are not shown as highlights."""
    labels: list[str] = []
    seen: set[str] = set()
    for skill in match.get("matched_skills") or []:
        text = str(skill).strip()
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            labels.append(text)
    for item in match.get("semantic_matches") or []:
        if not isinstance(item, dict):
            continue
        text = str(item.get("required_skill") or item.get("candidate_skill") or "").strip()
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            labels.append(text)
    return labels[:3]


def _avatar(job: dict) -> str:
    badge = initials(str(job.get("company") or job.get("title") or "Job"))
    return f"<span class='home-avatar'>{html.escape(badge or 'JB')}</span>"


def _match_preview(match: dict) -> str:
    job = match.get("job") or {}
    title = html.escape(str(job.get("title") or ""))
    company = html.escape(str(job.get("company") or ""))
    location = str(job.get("location") or "").strip()
    location_line = f"<p class='match-location'>{html.escape(location)}</p>" if location else ""
    chips = "".join(
        f"<span class='home-chip'>{html.escape(skill)}</span>" for skill in _match_highlights(match)
    )
    chip_row = f"<div class='home-chip-row'>{chips}</div>" if chips else ""
    return (
        "<div class='home-match-card'>"
        "<div class='home-match-top'>"
        f"{_avatar(job)}"
        "<div class='home-match-copy'>"
        f"<h3 class='match-title home-recent-job'>{title}</h3>"
        f"<p class='match-company'>{company}</p>"
        f"{location_line}"
        "</div>"
        f"{_score_ring(match['total_score'])}"
        "</div>"
        f"{chip_row}"
        "</div>"
    )


_BOOKMARK_ICON = (
    "<svg class='home-icon' viewBox='0 0 24 24' aria-hidden='true'>"
    "<path d='M7 4h10a1 1 0 0 1 1 1v15l-6-3.2L6 20V5a1 1 0 0 1 1-1z'></path></svg>"
)
_CALENDAR_ICON = (
    "<svg class='home-icon' viewBox='0 0 24 24' aria-hidden='true'>"
    "<rect x='4' y='5' width='16' height='15' rx='2'></rect>"
    "<path d='M8 3v4M16 3v4M4 10h16'></path></svg>"
)


def _saved_preview(item: dict) -> str:
    job = item.get("job") or {}
    title = html.escape(str(job.get("title") or ""))
    company = html.escape(str(job.get("company") or ""))
    location = str(job.get("location") or "").strip()
    location_line = f"<p class='match-location'>{html.escape(location)}</p>" if location else ""
    saved_at = str(item.get("created_at") or "").replace("T", " ")[:16]
    saved_line = (
        f"<p class='saved-date'>{_CALENDAR_ICON} Saved {html.escape(saved_at)}</p>" if saved_at else ""
    )
    return (
        "<div class='home-saved-card'>"
        "<div class='home-saved-top'>"
        f"{_avatar(job)}"
        "<div class='home-match-copy'>"
        f"<h3 class='match-title home-saved-job'>{title}</h3>"
        f"<p class='match-company'>{company}</p>"
        f"{location_line}"
        "</div>"
        f"<span class='home-bookmark'>{_BOOKMARK_ICON}</span>"
        "</div>"
        "<hr class='home-divider'>"
        f"{saved_line}"
        "</div>"
    )


def _prepare_profile_choices() -> None:
    """Keep the suggestion lists, including any custom entries added in this session."""
    defaults = {
        "skill_choices": list(SKILL_OPTIONS),
        "role_choices": list(ROLE_OPTIONS),
        "location_choices": list(LOCATION_OPTIONS),
        "skill_notice": "",
        "role_notice": "",
        "location_notice": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _remember_custom(option_key: str, selected_key: str, text_key: str, notice_key: str, noun: str) -> None:
    """Store a custom entry before the dropdown is drawn again."""
    options, selected, notice = include_custom(
        list(st.session_state.get(option_key) or []),
        list(st.session_state.get(selected_key) or []),
        str(st.session_state.get(text_key) or ""),
        noun,
    )
    st.session_state[option_key] = options
    st.session_state[selected_key] = selected
    st.session_state[notice_key] = notice
    if not notice:
        st.session_state[text_key] = ""


def _choice_picker(
    label: str,
    options_key: str,
    selected_key: str,
    text_key: str,
    notice_key: str,
    noun: str,
    placeholder: str,
) -> list[str]:
    """Searchable multi-select plus a box for one custom entry."""
    selected = st.multiselect(
        label,
        st.session_state[options_key],
        key=selected_key,
        placeholder=placeholder,
    )
    entry_col, action_col = st.columns([4, 1], vertical_alignment="bottom")
    with entry_col:
        st.text_input(f"Add a {noun}", key=text_key, placeholder=f"Type a {noun} that is not listed")
    with action_col:
        st.button(
            f"Add {noun}",
            on_click=_remember_custom,
            args=(options_key, selected_key, text_key, notice_key, noun),
        )
    notice = st.session_state.get(notice_key) or ""
    if notice:
        st.warning(notice)
    return list(selected)


def _prefill_profile_form() -> None:
    """Fill the form from the saved profile once, without wiping later edits."""
    if st.session_state.get("_profile_form_ready"):
        return
    profile = st.session_state.get("profile") or {}
    if not profile:
        return
    st.session_state._profile_form_ready = True
    st.session_state.profile_name = profile.get("name") or ""
    st.session_state.profile_email = profile.get("email") or ""
    education = profile.get("education") or ""
    if not education:
        st.session_state.profile_education = "Not specified"
    elif education in EDUCATION_OPTIONS and education != "Other":
        st.session_state.profile_education = education
    else:
        st.session_state.profile_education = "Other"
        st.session_state["custom_education"] = education
    years = int(profile.get("years_experience") or 0)
    st.session_state.profile_years = years if years in EXPERIENCE_YEARS else 0
    _prefill_choice("profile_degree", "custom_degree", profile.get("degree"), DEGREE_OPTIONS)
    _prefill_choice("profile_field", "custom_field", profile.get("field_of_study"), FIELD_OPTIONS)
    st.session_state.profile_specialization = profile.get("specialization") or ""
    st.session_state.profile_institution = profile.get("institution") or ""
    graduation = profile.get("graduation_year")
    st.session_state.profile_graduation = "" if graduation in (None, "") else str(graduation)
    remote = str(profile.get("remote_preference") or "").casefold()
    st.session_state.profile_remote = {"remote": "Remote", "hybrid": "Hybrid", "onsite": "Onsite"}.get(remote, "Not specified")
    st.session_state.profile_industries = [str(item) for item in (profile.get("preferred_industries") or []) if str(item).strip()]
    st.session_state.profile_countries = [str(item) for item in (profile.get("preferred_countries") or []) if str(item).strip()]
    groups = (
        ("skills", "skill_choices", "profile_skills"),
        ("preferred_roles", "role_choices", "profile_roles"),
        ("preferred_locations", "location_choices", "profile_locations"),
    )
    for field, options_key, selected_key in groups:
        selected = [str(item) for item in (profile.get(field) or []) if str(item).strip()]
        options = list(st.session_state.get(options_key) or [])
        for item in selected:
            if all(option.casefold() != item.casefold() for option in options):
                options.append(item)
        st.session_state[options_key] = options
        st.session_state[selected_key] = selected


def page_profile() -> None:
    """Edit the signed-in profile in place. The header uses the last saved record."""
    page_header(
        "My Profile",
        "Update the details saved on your account. Your login email stays the same.",
        "Profile",
    )
    st.markdown("<div class='profile-dashboard'></div>", unsafe_allow_html=True)
    notice = st.session_state.pop("_profile_notice", None)
    warning = st.session_state.pop("_profile_warning", None)
    if warning:
        st.warning(warning)
    if notice:
        st.success(notice)
    _prepare_profile_choices()
    _prefill_profile_form()
    profile = st.session_state.get("profile")
    _render_profile_header(profile if isinstance(profile, dict) else None)
    locked = isinstance(profile, dict) and bool(_display_text(profile.get("email")))
    _render_profile_editor(locked)
    render_change_password()


def _render_profile_header(profile: dict | None) -> None:
    with st.container(border=True):
        if not isinstance(profile, dict):
            st.markdown(
                (
                    "<p class='section-label profile-overview'>Profile overview</p>"
                    "<p class='hero-lead'>No saved profile is loaded, so the completion "
                    "percentage stays hidden.</p>"
                ),
                unsafe_allow_html=True,
            )
            return
        sections = profile_sections(profile)
        percent = completion_percent(sections)
        name = _display_text(profile.get("name")) or "Name not saved"
        email = _display_text(profile.get("email")) or "Email not saved"
        education = _display_text(profile.get("education")) or "Not specified"
        years = experience_text(profile.get("years_experience")) or "Not saved yet"
        mark = html.escape(initials(name) or "•")
        st.markdown(
            (
                "<div class='profile-identity'>"
                f"<div class='avatar'>{mark}</div>"
                "<div>"
                "<p class='section-label profile-overview'>Candidate Profile</p>"
                f"<h3 class='match-title'>{html.escape(name)}</h3>"
                f"<p class='match-company'>{html.escape(email)}</p>"
                "</div></div>"
                f"<p class='detail-line'>Education: {html.escape(education)}</p>"
                f"<p class='detail-line'>Years of experience: {html.escape(years)}</p>"
                "<p class='section-label profile-completion'>Profile completion</p>"
                f"<p class='profile-percent'>{percent}%</p>"
                "<span class='progress-track'>"
                f"<span class='progress-fill' style='width: {percent}%'></span>"
                "</span>"
                f"<p class='hero-lead'>{filled_section_count(sections)} of {len(sections)} sections filled</p>"
            ),
            unsafe_allow_html=True,
        )
        saved_skills = _clean_items(profile.get("skills"))
        if saved_skills:
            chips(saved_skills, "exact")
        else:
            st.markdown("<p class='hero-lead'>No skills saved yet.</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='hero-lead'>{html.escape(SKILL_NOTE)}</p>", unsafe_allow_html=True)
        saved_locations = _clean_items(profile.get("preferred_locations"))
        if saved_locations:
            chips(saved_locations, "semantic")
        suggestions = section_suggestions(sections)
        if suggestions:
            st.markdown("<p class='section-label profile-completion'>Suggestions</p>", unsafe_allow_html=True)
            for hint in suggestions:
                st.markdown(f"<p class='hero-lead'>{html.escape(hint)}</p>", unsafe_allow_html=True)
        with st.expander("How is profile completion calculated?"):
            criteria = "".join(
                f"<li>{html.escape(section['label'])}</li>" for section in sections
            )
            st.markdown(
                (
                    f"<p class='completion-help'>{html.escape(COMPLETION_EXPLANATION)}</p>"
                    f"<ul class='completion-criteria'>{criteria}</ul>"
                ),
                unsafe_allow_html=True,
            )
        st.markdown(
            f"<div class='completion-grid'>{''.join(_completion_item(section) for section in sections)}</div>",
            unsafe_allow_html=True,
        )


def _completion_item(section: dict) -> str:
    """One status tile. The filled flag comes from the saved profile sections."""
    filled = bool(section["complete"])
    state = "Filled" if filled else "Not saved"
    kind = "completion-filled" if filled else "completion-open"
    icon = _CHECK_ICON if filled else _OPEN_ICON
    return (
        f"<div class='completion-item {kind}'>"
        f"<span class='completion-icon' aria-hidden='true'>{icon}</span>"
        f"<span class='completion-name'>{html.escape(section['label'])}</span>"
        f"<span class='completion-state'>{state}</span>"
        "</div>"
    )


_CHECK_ICON = (
    "<svg viewBox='0 0 24 24'><path d='M5 12.5l4.2 4.2L19 7.2'></path></svg>"
)
_OPEN_ICON = (
    "<svg viewBox='0 0 24 24'><circle cx='12' cy='12' r='7'></circle></svg>"
)


def _prefill_choice(choice_key: str, custom_key: str, value, options: list[str]) -> None:
    """Restore a suggestion or keep a custom value that is not in the list."""
    text = " ".join(str(value).split()) if value else ""
    if not text:
        st.session_state[choice_key] = "Not specified"
        return
    match = next((item for item in options if item.casefold() == text.casefold() and item != "Other"), None)
    if match:
        st.session_state[choice_key] = match
        return
    st.session_state[choice_key] = "Other"
    st.session_state[custom_key] = text


def _capture_draft() -> None:
    """Copy widget values into ordinary session state before a step change.

    Streamlit drops a widget key when that control is not drawn on the next
    step. The draft keeps the earlier answers so saving does not wipe them.
    """
    draft = dict(st.session_state.get("profile_draft") or {})
    for key in (
        "profile_name",
        "profile_email",
        "profile_education",
        "custom_education",
        "profile_years",
        "profile_degree",
        "custom_degree",
        "profile_field",
        "custom_field",
        "profile_specialization",
        "profile_institution",
        "profile_graduation",
        "profile_skills",
        "profile_roles",
        "profile_locations",
        "profile_industries",
        "profile_countries",
        "profile_remote",
    ):
        if key in st.session_state:
            draft[key] = st.session_state[key]
    st.session_state.profile_draft = draft


def _restore_draft() -> None:
    """Put drafted answers back before the controls that are on this step."""
    for key, value in dict(st.session_state.get("profile_draft") or {}).items():
        if key not in st.session_state:
            st.session_state[key] = value


def _set_builder_step(step: int) -> None:
    _capture_draft()
    st.session_state.profile_builder_step = step


def _clear_selected_skills() -> None:
    st.session_state.profile_skills = []


def _drafted(key: str, default):
    if key in st.session_state:
        return st.session_state[key]
    draft = st.session_state.get("profile_draft") or {}
    if key in draft:
        return draft[key]
    return default


def _session_text(key: str, default: str = "") -> str:
    value = _drafted(key, default)
    return "" if value is None else str(value)


def _session_list(key: str, saved_field: str) -> list[str]:
    """Use the current selection. Before that step is opened, keep the saved list."""
    if key in st.session_state or key in (st.session_state.get("profile_draft") or {}):
        return [str(item) for item in (_drafted(key, []) or [])]
    profile = st.session_state.get("profile") if isinstance(st.session_state.get("profile"), dict) else {}
    return [str(item) for item in (profile.get(saved_field) or []) if str(item).strip()]


def _load_builder_catalogue() -> str | None:
    """Read provider industries, covered countries, and stored job titles once."""
    if isinstance(st.session_state.get("builder_catalogue"), dict):
        return None
    filters, filter_error = authed_request("GET", "/jobs/filters")
    jobs, jobs_error = authed_request("GET", "/jobs/")
    if filter_error and jobs_error:
        return filter_error
    catalogue = {"industries": [], "countries": [], "titles": [], "skill_names": []}
    if isinstance(filters, dict):
        for item in filters.get("categories") or []:
            if isinstance(item, dict) and str(item.get("value") or "").strip() and str(item.get("label") or "").strip():
                catalogue["industries"].append({"tag": str(item["value"]).strip(), "label": str(item["label"]).strip()})
        for item in filters.get("countries") or []:
            if isinstance(item, dict) and str(item.get("value") or "").strip() and str(item.get("label") or "").strip():
                catalogue["countries"].append({"code": str(item["value"]).strip(), "label": str(item["label"]).strip()})
    titles: list[str] = []
    skill_names: list[str] = []
    if isinstance(jobs, list):
        for job in jobs:
            if not isinstance(job, dict):
                continue
            title = " ".join(str(job.get("title") or "").split())
            if title:
                titles.append(title)
            for skill in job.get("required_skills") or []:
                cleaned = " ".join(str(skill).split())
                if cleaned and cleaned.casefold() != "none":
                    skill_names.append(cleaned)
    catalogue["titles"] = titles
    catalogue["skill_names"] = skill_names
    st.session_state.builder_catalogue = catalogue
    return filter_error


def _merge_choices(options_key: str, extras: list[str]) -> None:
    options = list(st.session_state.get(options_key) or [])
    for item in extras:
        cleaned = " ".join(str(item).split())
        if cleaned and all(option.casefold() != cleaned.casefold() for option in options):
            options.append(cleaned)
    st.session_state[options_key] = options


def _render_builder_progress(step: int) -> None:
    labels = ["Education", "Skills", "Career", "Location"]
    pieces = []
    for index, label in enumerate(labels, start=1):
        kind = " current" if step == index or (step > 4 and index == 4) else ""
        pieces.append(f"<span class='builder-step{kind}'>{index}. {html.escape(label)}</span>")
    st.markdown(f"<div class='builder-steps'>{''.join(pieces)}</div>", unsafe_allow_html=True)


def _render_optional_choice(label: str, choice_key: str, custom_key: str, options: list[str], noun: str) -> None:
    choice = st.selectbox(label, options, key=choice_key)
    if choice == "Other":
        st.text_input(f"Custom {noun}", key=custom_key, placeholder=f"Type a {noun}")


def _render_profile_editor(email_locked: bool) -> None:
    """Four guided steps plus a review. Each step can save the whole profile."""
    _restore_draft()
    step = int(st.session_state.get("profile_builder_step") or 1)
    if step < 1 or step > 5:
        step = 1
        st.session_state.profile_builder_step = 1
    _render_builder_progress(step)
    catalogue_error = _load_builder_catalogue()
    catalogue = st.session_state.get("builder_catalogue") if isinstance(st.session_state.get("builder_catalogue"), dict) else {}
    _merge_choices("skill_choices", list(SKILL_OPTIONS) + list(catalogue.get("skill_names") or []))
    _merge_choices("role_choices", list(ROLE_OPTIONS) + list(catalogue.get("titles") or []))
    # Every step stays registered so a selection is not dropped when it is collapsed.
    with st.expander("Education and background", expanded=step == 1):
        _render_education_step(email_locked)
    with st.expander("Skills", expanded=step == 2):
        _render_skills_step()
    with st.expander("Career preferences", expanded=step == 3):
        _render_career_step(catalogue_error)
    with st.expander("Location preferences", expanded=step == 4):
        _render_location_step(catalogue_error)
    with st.expander("Profile summary", expanded=step == 5):
        _render_profile_summary()
    back_col, next_col, skip_col, save_col = st.columns(4)
    with back_col:
        st.button("Back", disabled=step == 1, on_click=_set_builder_step, args=(max(1, step - 1),))
    with next_col:
        if step < 5:
            st.button("Continue", on_click=_set_builder_step, args=(step + 1,))
    with skip_col:
        if step == 1:
            st.button("Skip optional fields", on_click=_set_builder_step, args=(2,))
    with save_col:
        submitted = st.button("Save Changes", type="primary")
    _capture_draft()
    if not submitted:
        return
    _save_profile()


def _render_education_step(email_locked: bool) -> None:
    with st.container(border=True):
        st.markdown(
            (
                "<p class='section-label profile-card profile-builder'>Education and background</p>"
                "<p class='form-hint'>Name can be updated. Email stays the address you used to log in. "
                "Degree, field, specialization, institution, and graduation year can be left blank.</p>"
            ),
            unsafe_allow_html=True,
        )
        left, right = st.columns(2, gap="large")
        with left:
            st.text_input("Name", key="profile_name")
            education_choice = st.selectbox("Education", EDUCATION_OPTIONS, key="profile_education")
            _render_optional_choice("Degree", "profile_degree", "custom_degree", DEGREE_OPTIONS, "degree")
            _render_optional_choice("Field of study", "profile_field", "custom_field", FIELD_OPTIONS, "field of study")
        with right:
            st.text_input("Email", key="profile_email", disabled=email_locked)
            st.selectbox(
                "Years of experience",
                EXPERIENCE_YEARS,
                key="profile_years",
                format_func=lambda years: "Less than 1 year" if years == 0 else f"{years} {'year' if years == 1 else 'years'}",
            )
            st.text_input("Specialization", key="profile_specialization", placeholder="Optional")
            st.text_input("Institution", key="profile_institution", placeholder="Optional")
            st.text_input("Graduation year", key="profile_graduation", placeholder="Optional, for example 2024")
        if education_choice == "Other":
            st.text_input("Custom education", key="custom_education", placeholder="Type your qualification")


def _render_skills_step() -> None:
    with st.container(border=True):
        st.markdown(
            (
                "<p class='section-label profile-card'>Skills</p>"
                f"<p class='hero-lead'>{html.escape(SKILL_NOTE)}</p>"
                "<p class='hero-lead'>Search the suggestions, add your own, and remove a skill from the selection before saving.</p>"
            ),
            unsafe_allow_html=True,
        )
        selected = _session_list("profile_skills", "skills")
        if selected:
            chips(selected, "exact")
        else:
            st.markdown("<p class='hero-lead'>No skills selected yet.</p>", unsafe_allow_html=True)
        _choice_picker(
            "Skills",
            "skill_choices",
            "profile_skills",
            "custom_skill",
            "skill_notice",
            "skill",
            "Search skills",
        )
        st.button("Remove selected skills", on_click=_clear_selected_skills)
        with st.expander("Suggested skills"):
            st.markdown("<p class='hero-lead'>Suggestions come from the skill list and skills stored on job listings.</p>", unsafe_allow_html=True)


def _render_career_step(catalogue_error: str | None) -> None:
    catalogue = st.session_state.get("builder_catalogue") if isinstance(st.session_state.get("builder_catalogue"), dict) else {}
    industries = list(catalogue.get("industries") or [])
    with st.container(border=True):
        st.markdown(
            (
                "<p class='section-label profile-card'>Career preferences</p>"
                "<p class='hero-lead'>Industries come from the provider category catalogue. "
                "They can be used in Discover Jobs. They do not change the match score.</p>"
            ),
            unsafe_allow_html=True,
        )
        if industries:
            labels = {item["tag"]: item["label"] for item in industries}
            options = [item["tag"] for item in industries]
            for saved in _session_list("profile_industries", "preferred_industries"):
                if saved not in options:
                    options.append(saved)
                    labels.setdefault(saved, saved)
            st.multiselect(
                "Preferred industries",
                options,
                key="profile_industries",
                format_func=lambda tag: labels.get(tag, tag),
                placeholder="Search industries",
            )
        else:
            st.markdown(
                "<p class='hero-lead'>The industry catalogue is not available right now, so no industries are listed.</p>",
                unsafe_allow_html=True,
            )
            if catalogue_error:
                st.warning(catalogue_error)
        _choice_picker(
            "Preferred roles",
            "role_choices",
            "profile_roles",
            "custom_role",
            "role_notice",
            "role",
            "Search roles",
        )
        with st.expander("Role suggestions"):
            st.markdown(
                "<p class='hero-lead'>Suggestions include titles from stored listings and roles already saved on your profile. A custom role is kept.</p>",
                unsafe_allow_html=True,
            )


def _render_location_step(catalogue_error: str | None) -> None:
    catalogue = st.session_state.get("builder_catalogue") if isinstance(st.session_state.get("builder_catalogue"), dict) else {}
    countries = list(catalogue.get("countries") or [])
    with st.container(border=True):
        st.markdown(
            (
                "<p class='section-label profile-card'>Location preferences</p>"
                "<p class='hero-lead'>Live provider coverage currently includes India and the United Kingdom. "
                "A country appears here when the provider configuration includes it. "
                "Cities and regions are used for location matching. Remote preference is stored separately and does not change the match score.</p>"
            ),
            unsafe_allow_html=True,
        )
        if countries:
            labels = {item["code"]: item["label"] for item in countries}
            options = [item["code"] for item in countries]
            for saved in _session_list("profile_countries", "preferred_countries"):
                if saved not in options:
                    options.append(saved)
                    labels.setdefault(saved, saved)
            st.multiselect(
                "Preferred countries",
                options,
                key="profile_countries",
                format_func=lambda code: labels.get(code, code),
                placeholder="Search countries",
            )
        else:
            st.markdown(
                "<p class='hero-lead'>Country coverage is not available right now, so no countries are listed.</p>",
                unsafe_allow_html=True,
            )
            if catalogue_error:
                st.warning(catalogue_error)
        st.selectbox("Remote preference", REMOTE_OPTIONS, key="profile_remote")
        _choice_picker(
            "Preferred locations",
            "location_choices",
            "profile_locations",
            "custom_location",
            "location_notice",
            "location",
            "Search cities",
        )


def _render_profile_summary() -> None:
    with st.container(border=True):
        st.markdown(
            (
                "<p class='section-label profile-card'>Profile summary</p>"
                "<p class='hero-lead'>This is the profile that will be saved. Match scores still use skills, preferred roles, and preferred locations only.</p>"
            ),
            unsafe_allow_html=True,
        )
        rows = [
            ("Name", _session_text("profile_name") or "Not entered"),
            ("Email", _session_text("profile_email") or "Not entered"),
            ("Education", _session_text("profile_education", "Not specified")),
            ("Degree", _session_text("profile_degree", "Not specified")),
            ("Field of study", _session_text("profile_field", "Not specified")),
            ("Specialization", _session_text("profile_specialization") or "Not entered"),
            ("Institution", _session_text("profile_institution") or "Not entered"),
            ("Graduation year", _session_text("profile_graduation") or "Not entered"),
            ("Experience", _session_text("profile_years", "0")),
            ("Remote preference", _session_text("profile_remote", "Not specified")),
        ]
        for label, value in rows:
            st.markdown(f"<p class='detail-line'>{html.escape(label)}: {html.escape(value)}</p>", unsafe_allow_html=True)
        for label, key, field in (
            ("Skills", "profile_skills", "skills"),
            ("Roles", "profile_roles", "preferred_roles"),
            ("Industries", "profile_industries", "preferred_industries"),
            ("Countries", "profile_countries", "preferred_countries"),
            ("Locations", "profile_locations", "preferred_locations"),
        ):
            values = _session_list(key, field)
            st.markdown(
                f"<p class='detail-line'>{html.escape(label)}: {html.escape(', '.join(values) if values else 'None selected')}</p>",
                unsafe_allow_html=True,
            )


def _save_profile() -> None:
    payload, validation_error = profile_payload(
        _session_text("profile_name"),
        _session_text("profile_email"),
        _session_text("profile_education", "Not specified"),
        _session_text("custom_education"),
        _session_list("profile_skills", "skills"),
        _session_list("profile_roles", "preferred_roles"),
        _session_list("profile_locations", "preferred_locations"),
        int(_session_text("profile_years", "0") or 0),
        degree_choice=_session_text("profile_degree", "Not specified"),
        custom_degree=_session_text("custom_degree"),
        field_choice=_session_text("profile_field", "Not specified"),
        custom_field=_session_text("custom_field"),
        specialization=_session_text("profile_specialization"),
        institution=_session_text("profile_institution"),
        graduation_year=_session_text("profile_graduation"),
        preferred_industries=_session_list("profile_industries", "preferred_industries"),
        preferred_countries=_session_list("profile_countries", "preferred_countries"),
        remote_choice=_session_text("profile_remote", "Not specified"),
    )
    if validation_error:
        st.error(validation_error)
        return
    with st.spinner("Saving your profile."):
        created, create_error = authed_request(
            "PATCH",
            f"/candidates/{st.session_state.candidate_id}",
            payload,
        )
        confirmed = None
        confirm_error = None
        if create_error is None and isinstance(created, dict) and created.get("id") is not None:
            confirmed, confirm_error = authed_request("GET", f"/candidates/{created['id']}")
    if create_error or not isinstance(created, dict):
        st.error(create_error or "The profile could not be saved.")
        return
    st.session_state.candidate_id = created["id"]
    st.session_state.candidate_name = created["name"]
    st.session_state.profile = created
    st.session_state.matches = None
    st.session_state.saved_jobs = None
    if confirm_error:
        st.session_state._profile_warning = confirm_error
    elif isinstance(confirmed, dict):
        st.session_state.profile = confirmed
        st.session_state.candidate_name = confirmed.get("name") or created["name"]
        pending = [
            key
            for key in (
                "degree",
                "field_of_study",
                "specialization",
                "institution",
                "graduation_year",
                "preferred_industries",
                "preferred_countries",
                "remote_preference",
            )
            if payload.get(key) not in (None, [], "") and key not in confirmed
        ]
        if pending:
            st.session_state._profile_warning = (
                "The current API saved your existing profile fields. "
                "The new education, industry, country, and remote fields are waiting for the profile migration."
            )
    st.session_state._profile_notice = (
        f"Profile saved. Your candidate id is {st.session_state.candidate_id}. "
        "Open Match Insights next."
    )
    st.session_state._profile_form_ready = False
    st.rerun()


def _display_text(value) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())


def _clean_items(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [cleaned for item in value if (cleaned := _display_text(item))]


def _load_cached_list(state_key: str, path: str, failure: str, waiting: str) -> str | None:
    """Read one list once per session. A failed response is not stored as an empty list."""
    if st.session_state.get(state_key) is not None:
        return None
    with st.spinner(waiting):
        body, error = authed_request("GET", path)
    if error is None and isinstance(body, list):
        st.session_state[state_key] = body
        return None
    return error or failure


def _clear_discover_filters() -> None:
    st.session_state.discover_query = ""
    st.session_state.discover_industry = "all"
    st.session_state.discover_country = "worldwide"
    st.session_state.discover_location_text = ""
    st.session_state.discover_workplace = "any"
    st.session_state.discover_employment = "any"
    st.session_state.discover_experience_band = "any"
    st.session_state.discover_salary_currency = "any"
    st.session_state.discover_salary_min = ""
    st.session_state.discover_salary_max = ""
    st.session_state.discover_sort = "newest"


def _select_job(job_id: int) -> None:
    st.session_state.selected_job_id = job_id


def page_discover() -> None:
    """Search stored listings and show scores from the matching service."""
    page_header(
        "Discover Jobs",
        "Search the stored listings. A keyword search for India or the United Kingdom also checks Jooble live results.",
        "Jobs",
    )
    st.markdown("<div class='discover-page'></div>", unsafe_allow_html=True)
    filters_error = _load_discover_filters()
    saved_error = _load_cached_list(
        "saved_jobs",
        f"/candidates/{st.session_state.candidate_id}/saved-jobs",
        "Saved jobs could not be read.",
        "Loading saved jobs.",
    )
    choices = _discover_choices()
    query, industry, country, location_text, workplace, employment, experience, currency, salary_min, salary_max, sort_by = _discover_controls(choices)
    params = _discover_params(
        query, industry, country, location_text, workplace, employment, experience, currency, salary_min, salary_max
    )
    jobs, jobs_error = _load_discover_results(params)
    if jobs_error or not isinstance(jobs, list):
        st.error(jobs_error or "The job list could not be read.")
        return
    live_jobs, live_error = _load_jooble_results(query, country, location_text, industry)
    if live_error:
        st.warning(live_error)
    if live_jobs:
        jobs = [*jobs, *omit_repeated_jobs(jobs, live_jobs)]
    if filters_error:
        st.warning(filters_error)
    if saved_error:
        st.warning(saved_error)
    noun = "listing" if len(jobs) == 1 else "listings"
    st.markdown(
        f"<p class='status-line'>{len(jobs)} {noun} match.</p>",
        unsafe_allow_html=True,
    )
    if not jobs:
        with st.container(border=True):
            if set(params) == {"sort"}:
                empty_state(
                    "No jobs are stored yet",
                    "Listings will appear here when the catalog has jobs.",
                    "discover-empty",
                )
            else:
                empty_state(
                    "No listings match these filters",
                    "Try another industry, country, or location. A category can be empty when no stored listing belongs to it.",
                    "discover-empty",
                )
        return
    match_error = _load_discover_matches()
    if match_error:
        st.warning(match_error)
    ranked = matches_by_job(st.session_state.get("matches"))
    visible = _sort_discover_jobs(jobs, sort_by, ranked)
    saved_ids = saved_job_ids(st.session_state.get("saved_jobs"))
    selected = next((job for job in jobs if job_key(job.get("id")) == job_key(st.session_state.get("selected_job_id"))), None)
    if selected is not None:
        _render_job_detail(selected, ranked.get(job_key(selected.get("id"))))
        _render_preparation(selected)
    _render_job_grid(visible, ranked, saved_ids)


def _load_discover_filters() -> str | None:
    """Read industry and country choices once per session."""
    if isinstance(st.session_state.get("discover_filters"), dict):
        return None
    body, error = authed_request("GET", "/jobs/filters")
    if error is None and isinstance(body, dict):
        st.session_state.discover_filters = body
        return None
    st.session_state.discover_filters = {
        "categories": [],
        "countries": [],
        "workplaces": [],
        "employment_types": [],
        "experience": [{"value": "any", "label": "Any"}],
        "salary_currencies": [],
        "sorts": [{"value": "newest", "label": "Newest first"}, {"value": "match_score", "label": "Match score"}],
        "category_status": "unavailable",
    }
    return error or "Industry categories could not be loaded."


def _discover_choices() -> dict:
    meta = st.session_state.get("discover_filters")
    if not isinstance(meta, dict):
        meta = {}
    return {
        "categories": _choice_rows(meta.get("categories")),
        "countries": _choice_rows(meta.get("countries")),
        "workplaces": _choice_rows(meta.get("workplaces")),
        "employment_types": _choice_rows(meta.get("employment_types")),
        "experience": _choice_rows(meta.get("experience")) or [{"value": "any", "label": "Any"}],
        "salary_currencies": [str(item) for item in meta.get("salary_currencies") or [] if str(item).strip()],
        "sorts": _choice_rows(meta.get("sorts")) or [{"value": "newest", "label": "Newest first"}],
        "category_status": meta.get("category_status") or "ready",
    }


def _choice_rows(value) -> list[dict]:
    if not isinstance(value, list):
        return []
    rows = []
    for item in value:
        if not isinstance(item, dict):
            continue
        token = str(item.get("value") or "").strip()
        label = str(item.get("label") or "").strip()
        if token and label:
            rows.append({"value": token, "label": label})
    return rows


def _discover_controls(choices: dict):
    industries = [{"value": "all", "label": "All industries"}, *choices["categories"], {"value": "unspecified", "label": "Other / Not specified"}]
    countries = [{"value": "worldwide", "label": "Worldwide"}, *choices["countries"]]
    workplaces = [{"value": "any", "label": "Any"}, *choices["workplaces"]]
    employment_types = [{"value": "any", "label": "Any"}, *choices["employment_types"]]
    experience = choices["experience"]
    sorts = choices["sorts"]
    _keep_choice("discover_industry", industries, "all")
    _keep_choice("discover_country", countries, "worldwide")
    _keep_choice("discover_workplace", workplaces, "any")
    _keep_choice("discover_employment", employment_types, "any")
    _keep_choice("discover_experience_band", experience, "any")
    _keep_choice("discover_sort", sorts, "newest")
    currencies = ["any", *choices["salary_currencies"]]
    if st.session_state.get("discover_salary_currency") not in currencies:
        st.session_state.discover_salary_currency = "any"
    with st.container(border=True):
        st.markdown("<p class='section-label discover-filters'>Search and filters</p>", unsafe_allow_html=True)
        query = st.text_input("Search jobs", key="discover_query", placeholder="Title, company, or skill")
        industry_col, country_col, location_col = st.columns(3)
        with industry_col:
            industry = st.selectbox("Industry", [item["value"] for item in industries], key="discover_industry", format_func=_label_for(industries))
            saved_profile = st.session_state.get("profile") if isinstance(st.session_state.get("profile"), dict) else {}
            known = {item["value"] for item in industries}
            saved_industries = [
                str(item) for item in (saved_profile.get("preferred_industries") or []) if str(item).strip() in known
            ]
            if saved_industries:
                st.caption("Your saved industries can be selected here. They do not change the match score.")
        with country_col:
            country = st.selectbox("Country", [item["value"] for item in countries], key="discover_country", format_func=_label_for(countries))
        with location_col:
            location_text = st.text_input("Location", key="discover_location_text", placeholder="City, state, or region")
        workplace_col, employment_col, experience_col = st.columns(3)
        with workplace_col:
            workplace = st.selectbox("Work arrangement", [item["value"] for item in workplaces], key="discover_workplace", format_func=_label_for(workplaces))
            if len(workplaces) == 1:
                st.caption("Stored listings do not include a workplace.")
        with employment_col:
            employment = st.selectbox("Employment type", [item["value"] for item in employment_types], key="discover_employment", format_func=_label_for(employment_types))
            if len(employment_types) == 1:
                st.caption("Stored listings do not include an employment type.")
        with experience_col:
            experience = st.selectbox("Experience", [item["value"] for item in experience], key="discover_experience_band", format_func=_label_for(experience))
        salary_col, sort_col, clear_col = st.columns([2, 2, 1], vertical_alignment="bottom")
        salary_min = ""
        salary_max = ""
        with salary_col:
            if choices["salary_currencies"]:
                currency = st.selectbox(
                    "Salary currency",
                    currencies,
                    key="discover_salary_currency",
                    format_func=lambda value: "Any currency" if value == "any" else value,
                )
                if currency != "any":
                    bound_col, upper_col = st.columns(2)
                    with bound_col:
                        salary_min = st.text_input("Minimum salary", key="discover_salary_min")
                    with upper_col:
                        salary_max = st.text_input("Maximum salary", key="discover_salary_max")
            else:
                currency = "any"
                st.caption("Salary is unavailable until a listing includes a currency.")
        with sort_col:
            sort_by = st.selectbox("Sort", [item["value"] for item in sorts], key="discover_sort", format_func=_label_for(sorts))
        with clear_col:
            st.button("Clear filters", on_click=_clear_discover_filters)
        if choices["category_status"] == "unavailable":
            st.caption("The provider category list could not be loaded. Listings without a stored category stay under Other / Not specified.")
    return query, industry, country, location_text, workplace, employment, experience, currency, salary_min, salary_max, sort_by


def _label_for(rows: list[dict]):
    labels = {item["value"]: item["label"] for item in rows}

    def format_choice(value: str) -> str:
        return labels.get(value, value)

    return format_choice


def _keep_choice(key: str, rows: list[dict], default: str) -> None:
    values = [item["value"] for item in rows]
    if st.session_state.get(key) not in values:
        st.session_state[key] = default if default in values else values[0]


def _discover_params(query, industry, country, location_text, workplace, employment, experience, currency, salary_min, salary_max) -> dict:
    params = {"sort": "newest"}
    if str(query or "").strip():
        params["q"] = str(query).strip()
    if industry not in {"", "all"}:
        params["category"] = industry
    if country not in {"", "worldwide"}:
        params["country"] = country
    if str(location_text or "").strip():
        params["location"] = str(location_text).strip()
    if workplace not in {"", "any"}:
        params["workplace"] = workplace
    if employment not in {"", "any"}:
        params["employment"] = employment
    if experience not in {"", "any"}:
        params["experience"] = experience
    if currency not in {"", "any"}:
        params["salary_currency"] = currency
        low = _salary_number(salary_min)
        high = _salary_number(salary_max)
        if low is not None:
            params["salary_min"] = low
        if high is not None:
            params["salary_max"] = high
    return params


def _salary_number(value) -> int | None:
    text = str(value or "").strip().replace(",", "")
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if number < 0:
        return None
    return int(number) if number.is_integer() else number


def _load_jooble_results(query, country, location_text, industry) -> tuple[list, str | None]:
    """Search one Jooble region. Worldwide and stored-only filters do not call Jooble."""
    code = str(country or "").strip().casefold()
    if code not in {"in", "gb"} or not str(query or "").strip():
        return [], None
    if industry not in {"", "all", "unspecified"}:
        return [], None
    params = {"country": code, "q": str(query).strip()}
    if str(location_text or "").strip():
        params["location"] = str(location_text).strip()
    body, error = authed_request("GET", f"/jobs/jooble?{urlencode(params)}")
    if error:
        return [], error
    if not isinstance(body, dict):
        return [], "Jooble search could not be read."
    rows = body.get("jobs")
    if not isinstance(rows, list):
        return [], "Jooble search could not be read."
    return [row for row in rows if isinstance(row, dict)], None


def _load_discover_results(params: dict):
    """Fetch one filtered result set and reuse it while the filters stay the same."""
    key = tuple(sorted((name, str(value)) for name, value in params.items()))
    cache = st.session_state.get("discover_results")
    if not isinstance(cache, dict):
        cache = {}
        st.session_state.discover_results = cache
    if key in cache and isinstance(cache[key], list):
        return cache[key], None
    body, error = authed_request("GET", f"/jobs/?{urlencode(params)}")
    if error is None and isinstance(body, list):
        cache[key] = body
        return body, None
    return None, error or "The job list could not be read."


def _sort_discover_jobs(jobs: list[dict], sort_by: str, ranked: dict) -> list[dict]:
    """Match-score order uses real scores. Listings without a score stay after them."""
    if sort_by != "match_score":
        return jobs

    def key(job):
        identifier = job_key(job.get("id"))
        number = identifier if isinstance(identifier, int) else 0
        if job_is_unmatchable(job):
            return (2, 0, number)
        match = ranked.get(identifier)
        score = match.get("total_score") if isinstance(match, dict) else None
        if not isinstance(score, (int, float)) or isinstance(score, bool):
            return (1, 0, number)
        return (0, -float(score), number)

    return sorted(jobs, key=key)


def _load_discover_matches() -> str | None:
    """Score matchable jobs once, then reuse that ranking on this page."""
    if st.session_state.get("matches") is not None:
        return None
    with st.spinner("Ranking matchable jobs. This can take a moment the first time."):
        found, error = authed_request(
            "GET",
            f"/candidates/{st.session_state.candidate_id}/matches",
            timeout=60,
        )
    if error is None and isinstance(found, list):
        st.session_state.matches = rankable_matches(found)
        return None
    return error or "Match scores could not be read."


def _render_job_detail(job: dict, match) -> None:
    with st.container(border=True):
        if job_is_unmatchable(job):
            score = unavailable_score_html("detail-score")
        elif isinstance(match, dict):
            score = (
                f"<p class='score-hero'>{html.escape(format_score(match['total_score']))}</p>"
                f"<p class='hero-lead'>{html.escape(match_quality(match['total_score']))}</p>"
            )
        else:
            score = "<p class='hero-lead'>This listing has not been ranked yet.</p>"
        description = html.escape(str(job.get("description") or "No description was stored."))
        if job.get("description_is_snippet"):
            description += "<p class='hero-lead'>The provider supplied a description snippet, not the full advertisement.</p>"
        st.markdown(
            (
                "<p class='section-label job-detail'>Job details</p>"
                f"{job_heading(job, 'job-detail')}"
                f"{score}"
                f"{listing_notes_html(job)}"
                f"<div class='insight-panel'>{description}</div>"
                f"{adzuna_attribution(job)}"
                f"{jooble_attribution(job)}"
                f"{original_listing_link(job)}"
            ),
            unsafe_allow_html=True,
        )
        if real_skills(job):
            chips(real_skills(job), "exact")


def _render_job_grid(jobs: list[dict], ranked: dict, saved_ids: set[int]) -> None:
    """Three cards per row. The last row keeps the same column width when fewer jobs remain."""
    with st.container():
        st.markdown("<div class='discover-grid'></div>", unsafe_allow_html=True)
        for start in range(0, len(jobs), 3):
            batch = jobs[start : start + 3]
            columns = st.columns(3, gap="medium")
            for column, job in zip(columns, batch):
                with column:
                    _render_job_card(job, ranked.get(job_key(job.get("id"))), job_key(job.get("id")) in saved_ids)


def _render_job_card(job: dict, match, already_saved: bool) -> None:
    with st.container(border=True):
        if job_is_unmatchable(job):
            score = unavailable_score_html()
        elif isinstance(match, dict):
            score = f"<p class='score-value discover-score'>Match {html.escape(format_score(match['total_score']))}</p>"
        else:
            score = "<p class='hero-lead discover-score'>Not ranked yet</p>"
        st.markdown(
            (
                f"{_card_heading(job)}"
                f"{score}"
                f"{listing_notes_html(job)}"
                f"{_jooble_snippet(job)}"
                f"{adzuna_attribution(job)}"
                f"{jooble_attribution(job)}"
                f"{original_listing_link(job)}"
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
        detail_col, save_col = st.columns(2)
        with detail_col:
            st.button("View details", key=f"detail-{job['id']}", on_click=_select_job, args=(job["id"],))
        with save_col:
            if not isinstance(job.get("id"), int):
                st.caption("Live results are not stored.")
            elif already_saved:
                st.button("Saved", key=f"saved-state-{job['id']}", disabled=True)
            elif st.button("Save Job", key=f"save-{job['id']}", type="primary"):
                save_job(job)


def _card_heading(job: dict) -> str:
    """Short card text. The details panel keeps the full title."""
    title = html.escape(short_text(job.get("title") or "Untitled role", 72))
    company_text = short_text(job.get("company") or "", 48)
    location_text = short_text(job.get("location") or "", 48)
    if str(job.get("source") or "").casefold() == "jooble":
        company_text = company_text or "Company not provided"
        location_text = location_text or "Location not provided"
    company = html.escape(company_text)
    location = location_text
    country_code = str(job.get("source_country") or "").strip().casefold()
    country = COUNTRY_NAMES.get(country_code, country_code.upper())
    if country and country.casefold() not in location.casefold():
        location = f"{location} · {country}" if location else country
    return (
        f"<h3 class='match-title discover-card'>{title}</h3>"
        f"<p class='match-company'>{company}</p>"
        f"<p class='match-location'>{html.escape(location)}</p>"
    )


def _plan_path(job_id: int) -> str:
    return f"/candidates/{st.session_state.candidate_id}/jobs/{job_id}/preparation"


def _store_plan(body: dict) -> None:
    cache = st.session_state.get("preparation_cache")
    if not isinstance(cache, dict):
        cache = {}
    cache[body.get("job_id")] = body
    st.session_state.preparation_cache = cache
    for task in body.get("tasks") or []:
        st.session_state[f"prep-task-{task['id']}"] = bool(task.get("completed"))
    job_id = body.get("job_id")
    notes_key = f"prep-notes-{job_id}"
    action_key = f"prep-action-{job_id}"
    if notes_key not in st.session_state:
        st.session_state[notes_key] = body.get("notes") or ""
    if action_key not in st.session_state:
        st.session_state[action_key] = body.get("next_action") or ""


def _load_plan(job_id: int):
    """Read one plan per job per session. A failed response is not cached."""
    cache = st.session_state.get("preparation_cache")
    if isinstance(cache, dict) and job_id in cache:
        return cache[job_id], None
    with st.spinner("Loading the preparation plan."):
        body, error = authed_request("GET", _plan_path(job_id))
    if error or not isinstance(body, dict):
        return None, error or "The preparation plan could not be read."
    _store_plan(body)
    return body, None


def _toggle_task(job_id: int, task_id: int) -> None:
    completed = bool(st.session_state.get(f"prep-task-{task_id}"))
    body, error = authed_request(
        "PATCH",
        f"{_plan_path(job_id)}/tasks/{task_id}",
        {"completed": completed},
    )
    if error or not isinstance(body, dict):
        st.session_state.prep_error = error or "The task could not be updated."
        st.session_state[f"prep-task-{task_id}"] = not completed
        return
    st.session_state.prep_error = None
    _store_plan(body)


def _add_task(job_id: int) -> None:
    label = st.session_state.get(f"prep-new-{job_id}", "")
    body, error = authed_request("POST", f"{_plan_path(job_id)}/tasks", {"label": label})
    if error or not isinstance(body, dict):
        st.session_state.prep_error = error or "The task could not be added."
        return
    st.session_state[f"prep-new-{job_id}"] = ""
    st.session_state.prep_error = None
    _store_plan(body)


def _delete_task(job_id: int, task_id: int) -> None:
    body, error = authed_request("DELETE", f"{_plan_path(job_id)}/tasks/{task_id}")
    if error or not isinstance(body, dict):
        st.session_state.prep_error = error or "The task could not be deleted."
        return
    st.session_state.prep_error = None
    _store_plan(body)


def _save_journal(job_id: int) -> None:
    body, error = authed_request(
        "PUT",
        _plan_path(job_id),
        {
            "notes": st.session_state.get(f"prep-notes-{job_id}", ""),
            "next_action": st.session_state.get(f"prep-action-{job_id}", ""),
        },
    )
    if error or not isinstance(body, dict):
        st.session_state.prep_error = error or "The notes could not be saved."
        return
    st.session_state.prep_error = None
    st.session_state.prep_notice = "Notes saved for this job."
    _store_plan(body)
    st.session_state[f"prep-notes-{job_id}"] = body.get("notes") or ""
    st.session_state[f"prep-action-{job_id}"] = body.get("next_action") or ""


def _jooble_snippet(job: dict) -> str:
    if str(job.get("source") or "").casefold() != "jooble":
        return ""
    text = " ".join(str(job.get("description") or "").split())
    if not text:
        return ""
    return f"<p class='detail-line'>{html.escape(short_text(text, 160))}</p>"


def _render_preparation(job: dict) -> None:
    """Show the signed-in candidate's plan for this job only."""
    job_id = job.get("id")
    if not isinstance(job_id, int):
        with st.container(border=True):
            st.caption("Live Jooble results stay on this page. They are not stored, so there is no preparation plan.")
        return
    plan, error = _load_plan(job_id)
    with st.container(border=True):
        st.markdown(
            (
                "<p class='section-label prep-plan'>My Preparation Plan</p>"
                "<p class='prep-note'>These tasks are suggestions for your own preparation. "
                "They are not the employer's selection process.</p>"
            ),
            unsafe_allow_html=True,
        )
        if error or not isinstance(plan, dict):
            st.error(error or "The preparation plan could not be read.")
            return
        if st.session_state.get("prep_error"):
            st.error(st.session_state.prep_error)
        if st.session_state.get("prep_notice"):
            st.success(st.session_state.prep_notice)
            st.session_state.prep_notice = None
        _render_plan_progress(plan)
        _render_plan_tasks(job_id, plan.get("tasks") or [])
        _render_plan_notes(job_id, plan)


def _render_plan_progress(plan: dict) -> None:
    fraction, counts, finished = progress_lines(plan.get("progress"))
    percent = int((plan.get("progress") or {}).get("percent") or 0)
    st.progress(min(max(percent, 0), 100) / 100, text=fraction)
    st.markdown(
        f"<p class='prep-count'>{html.escape(fraction)} · {html.escape(counts)}</p>",
        unsafe_allow_html=True,
    )
    if finished:
        st.markdown(
            "<p class='prep-done'>All preparation tasks for this job are complete.</p>",
            unsafe_allow_html=True,
        )


def _render_plan_tasks(job_id: int, tasks: list[dict]) -> None:
    if not tasks:
        empty_state(
            "No preparation tasks yet",
            "Add a task to start a plan for this job.",
            "prep-empty",
        )
    for task in tasks:
        task_id = task["id"]
        key = f"prep-task-{task_id}"
        if key not in st.session_state:
            st.session_state[key] = bool(task.get("completed"))
        if task.get("is_custom"):
            task_col, delete_col = st.columns([5, 1], vertical_alignment="center")
            with task_col:
                st.checkbox(
                    task["label"],
                    key=key,
                    on_change=_toggle_task,
                    args=(job_id, task_id),
                )
            with delete_col:
                st.button(
                    "Delete task",
                    key=f"prep-delete-{task_id}",
                    on_click=_delete_task,
                    args=(job_id, task_id),
                )
        else:
            st.checkbox(
                task["label"],
                key=key,
                on_change=_toggle_task,
                args=(job_id, task_id),
            )
    add_col, button_col = st.columns([4, 1], vertical_alignment="bottom")
    with add_col:
        st.text_input("Add a task", key=f"prep-new-{job_id}", placeholder="A step for this job")
    with button_col:
        st.button("Add task", key=f"prep-add-{job_id}", on_click=_add_task, args=(job_id,))


def _render_plan_notes(job_id: int, plan: dict) -> None:
    notes_key = f"prep-notes-{job_id}"
    action_key = f"prep-action-{job_id}"
    if notes_key not in st.session_state:
        st.session_state[notes_key] = plan.get("notes") or ""
    if action_key not in st.session_state:
        st.session_state[action_key] = plan.get("next_action") or ""
    st.markdown("<p class='section-label prep-notes'>My Notes</p>", unsafe_allow_html=True)
    st.text_area(
        "Journal",
        key=notes_key,
        height=140,
        placeholder=(
            "What I need to learn\n"
            "What I have already prepared\n"
            "Important points about this company\n"
            "Questions I want to ask"
        ),
    )
    next_task = plan.get("next_task") or {}
    next_label = next_task.get("label") or "Every task on this plan is finished."
    st.markdown(
        (
            "<div class='prep-next'>"
            "<p class='section-label'>What's Next?</p>"
            f"<p class='hero-lead'>{html.escape(str(next_label))}</p>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    st.text_input("My next action", key=action_key, placeholder="The next thing I will do for this job")
    st.button("Save notes and next action", key=f"prep-save-{job_id}", on_click=_save_journal, args=(job_id,))


def page_matches() -> None:
    """Explain one ranked job at a time. The numbers come from the match API."""
    page_header(
        "Match Insights",
        "See how your skills and preferences align with one stored job at a time.",
        "Ranking",
    )
    if not require_profile():
        return
    if st.session_state.matches is None:
        if st.button("Find matches", type="primary"):
            with st.spinner("Ranking jobs and writing explanations. This can take a moment."):
                found, match_error = authed_request(
                    "GET",
                    f"/candidates/{st.session_state.candidate_id}/matches",
                    timeout=60,
                )
            if match_error:
                st.error(match_error)
            else:
                st.session_state.matches = rankable_matches(found)
                st.rerun()
        with st.container(border=True):
            empty_state(
                "No ranking yet",
                "Choose Find matches to rank the jobs.",
                "match-empty",
            )
        return
    matches = rankable_matches(st.session_state.matches)
    if not matches:
        with st.container(border=True):
            empty_state(
                "No jobs yet",
                "No jobs are available yet.",
                "match-empty",
            )
        return
    ordered = sorted(matches, key=lambda item: (-float(item["total_score"]), int(item["job"]["id"])))
    labels = {
        match["job"]["id"]: f"{match['job']['title']} · {match['job']['company']}"
        for match in ordered
    }
    options = list(labels)
    if st.session_state.get("match_choice") not in labels:
        preferred = st.session_state.get("selected_match_id")
        st.session_state.match_choice = preferred if preferred in labels else options[0]
    with st.container(border=True):
        st.markdown("<p class='section-label match-controls'>Choose a job</p>", unsafe_allow_html=True)
        chosen_id = st.selectbox("Job", options, format_func=lambda job_id: labels[job_id], key="match_choice")
    match = next(item for item in ordered if item["job"]["id"] == chosen_id)
    total = match["total_score"]
    st.markdown(
        (
            "<p class='section-label'>Overall match</p>"
            f"<p class='score-hero'>{html.escape(format_score(total))}</p>"
            f"<p class='hero-lead'>{html.escape(match_quality(total))}</p>"
        ),
        unsafe_allow_html=True,
    )
    render_match_card(match)
    missing = [skill for skill in (match.get("missing_skills") or []) if str(skill).strip()]
    with st.container(border=True):
        st.markdown("<p class='section-label'>What is still open</p>", unsafe_allow_html=True)
        if missing:
            names = ", ".join(html.escape(str(skill)) for skill in missing)
            st.markdown(
                f"<p class='hero-lead'>These required skills are not matched yet: {names}.</p>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<p class='hero-lead'>Every listed required skill is matched.</p>",
                unsafe_allow_html=True,
            )


def page_saved() -> None:
    """List the jobs this profile has saved. Removal is not offered by the API."""
    page_header(
        "Saved Jobs",
        "Listings you saved, so you can come back to them later.",
        "Library",
    )
    st.markdown("<div class='saved-page discover-page'></div>", unsafe_allow_html=True)
    if not require_profile():
        return
    if st.session_state.saved_jobs is None:
        with st.spinner("Loading saved jobs."):
            saved, saved_error = authed_request(
                "GET",
                f"/candidates/{st.session_state.candidate_id}/saved-jobs",
            )
        if saved_error:
            st.error(saved_error)
        else:
            st.session_state.saved_jobs = saved
    saved_jobs = st.session_state.saved_jobs
    if saved_jobs is not None and not saved_jobs:
        with st.container(border=True):
            empty_state(
                "Nothing saved yet",
                "Jobs you save will appear here.",
                "saved-empty",
            )
            st.button("Discover Jobs", on_click=select_page, args=("Discover Jobs",), type="primary")
        return
    if not saved_jobs:
        return
    noun = "job" if len(saved_jobs) == 1 else "jobs"
    st.markdown(
        f"<p class='status-line'>{len(saved_jobs)} saved {noun}.</p>",
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        st.markdown("<p class='section-label saved-controls'>Find a saved role</p>", unsafe_allow_html=True)
        search_col, sort_col = st.columns([2, 1], gap="large")
        with search_col:
            query = st.text_input("Search saved jobs", placeholder="Title, company, location, or skill")
        with sort_col:
            sort_by = st.selectbox("Sort by", ["Recently saved", "Oldest saved", "Title", "Company"])
    visible = _sort_saved(_filter_saved(saved_jobs, query), sort_by)
    if query.strip() and not visible:
        with st.container(border=True):
            empty_state(
                "No matches",
                "No saved jobs match that search.",
                "saved-empty",
            )
        return
    ranked = matches_by_job(st.session_state.get("matches"))
    _render_saved_grid(visible, ranked)
    selected = next(
        (item for item in saved_jobs if (item.get("job") or {}).get("id") == st.session_state.get("selected_job_id")),
        None,
    )
    if selected is not None:
        _render_job_detail(selected["job"], ranked.get(selected["job"].get("id")))
        _render_preparation(selected["job"])
    st.caption("Removing a saved job is not available from the current API.")


def _render_saved_grid(items: list[dict], ranked: dict) -> None:
    """Three saved cards per row. The same grid rules used on Discover Jobs apply."""
    with st.container():
        st.markdown("<div class='discover-grid'></div>", unsafe_allow_html=True)
        for start in range(0, len(items), 3):
            batch = items[start : start + 3]
            columns = st.columns(3, gap="medium")
            for column, item in zip(columns, batch):
                job = item.get("job") or {}
                with column:
                    render_saved_card(item, ranked.get(job.get("id")), on_open=_select_job)


def _filter_matches(matches: list[dict], query: str) -> list[dict]:
    needle = query.strip().casefold()
    if not needle:
        return list(matches)
    kept = []
    for match in matches:
        job = match["job"]
        semantic = " ".join(
            f"{item.get('required_skill', '')} {item.get('candidate_skill', '')}"
            for item in match.get("semantic_matches") or []
        )
        haystack = " ".join(
            [
                str(job.get("title") or ""),
                str(job.get("company") or ""),
                str(job.get("location") or ""),
                " ".join(match.get("matched_skills") or []),
                " ".join(match.get("missing_skills") or []),
                semantic,
            ]
        ).casefold()
        if needle in haystack:
            kept.append(match)
    return kept


def _sort_matches(matches: list[dict], sort_by: str) -> list[dict]:
    if sort_by == "Title":
        return sorted(matches, key=lambda item: (item["job"]["title"].casefold(), item["job"]["id"]))
    if sort_by == "Skill score":
        return sorted(matches, key=lambda item: (-float(item["skill_score"]), item["job"]["id"]))
    return sorted(matches, key=lambda item: (-float(item["total_score"]), item["job"]["id"]))


def _sort_saved(saved_jobs: list[dict], sort_by: str) -> list[dict]:
    """Sort the jobs already returned. Recently saved keeps the API order."""
    if sort_by == "Title":
        return sorted(saved_jobs, key=lambda item: (item["job"]["title"].casefold(), item["job"]["id"]))
    if sort_by == "Company":
        return sorted(saved_jobs, key=lambda item: (item["job"]["company"].casefold(), item["job"]["id"]))
    if sort_by == "Oldest saved":
        return list(reversed(saved_jobs))
    return list(saved_jobs)


def _filter_saved(saved_jobs: list[dict], query: str) -> list[dict]:
    needle = query.strip().casefold()
    if not needle:
        return list(saved_jobs)
    kept = []
    for item in saved_jobs:
        job = item["job"]
        haystack = " ".join(
            [
                str(job.get("title") or ""),
                str(job.get("company") or ""),
                str(job.get("location") or ""),
                " ".join(job.get("required_skills") or []),
            ]
        ).casefold()
        if needle in haystack:
            kept.append(item)
    return kept
