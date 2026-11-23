"""Resume Centre. Extraction stays in this session and the original PDF is not stored."""

import hashlib
import html

import streamlit as st

from auth_session import authed_request, authed_upload
from components import chips, empty_state, page_header, select_page

MAX_RESUME_BYTES = 5 * 1024 * 1024
_UPLOAD_LIMIT_MB = 5


def page_resume() -> None:
    """A resume check and one-job comparison. The PDF is not stored."""
    page_header(
        "Resume Centre",
        "Review your resume or compare it with a job opportunity.",
    )
    st.markdown("<div class='resume-page'></div>", unsafe_allow_html=True)
    if not _resume_gate():
        return
    st.markdown(
        (
            "<p class='hero-lead resume-privacy'>Your original PDF isn't stored. "
            "Extracted text remains in your signed-in session and is cleared on logout.</p>"
        ),
        unsafe_allow_html=True,
    )
    with st.expander("Privacy details"):
        st.markdown(
            "The full resume is not sent to an external AI service. "
            "The original PDF is not saved. Extracted text stays in this signed-in session "
            "until you clear it or log out."
        )
    choice = st.radio(
        "Choose a step",
        ["Check My Resume", "Match My Resume to a Job"],
        horizontal=True,
        key="resume-section",
        label_visibility="collapsed",
    )
    if choice == "Match My Resume to a Job":
        _render_match()
    else:
        _render_health()


def _resume_gate() -> bool:
    """Open the page for this signed-in profile without repeating the sidebar name."""
    if st.session_state.candidate_id is None:
        with st.container(border=True):
            empty_state(
                "Profile needed",
                "Save a profile on My Profile first. Match Insights and Saved Jobs stay closed until then.",
                "gate-card",
            )
            st.button("Go to My Profile", on_click=select_page, args=("My Profile",), type="primary")
        return False
    return True


def clear_resume() -> None:
    """Remove the session resume without calling a storage API."""
    from auth_session import _clear_resume_state

    _clear_resume_state()
    st.session_state.resume_notice = None


def _render_health() -> None:
    resume = _render_upload()
    if resume is None:
        empty_state(
            "No resume uploaded",
            "Upload a text-based PDF to start the health check.",
            "resume-empty",
        )
        return
    _render_file_status(resume)
    health = resume.get("health") if isinstance(resume.get("health"), dict) else None
    if health is None:
        st.warning("Upload the resume again to calculate the health check.")
        return
    _render_health_summary(health)
    _render_improvement_checklist(health)


def _render_upload() -> dict | None:
    """Show the PDF control. A file is kept only after the existing checks succeed."""
    with st.container(border=True):
        st.markdown(
            (
                "<p class='section-label resume-heading'>Upload your resume</p>"
                "<p class='hero-lead resume-limit'>Text-based PDF only, up to 5 MB.</p>"
            ),
            unsafe_allow_html=True,
        )
        uploaded = st.file_uploader(
            "PDF resume",
            type=["pdf"],
            max_upload_size=_UPLOAD_LIMIT_MB,
            key=f"resume-file-{st.session_state.get('resume_uploader', 0)}",
            help="PDF only, up to 5 MB. The file itself is not stored.",
        )
        if uploaded is not None:
            size = uploaded.size if isinstance(getattr(uploaded, "size", None), int) else len(uploaded.getvalue())
            st.markdown(
                (
                    "<p class='hero-lead resume-file-selected'>Selected file: "
                    f"{html.escape(str(uploaded.name))} · {size} bytes.</p>"
                ),
                unsafe_allow_html=True,
            )
        _accept_upload(uploaded)
        resume = st.session_state.get("resume")
        notice = st.session_state.get("resume_notice")
        if isinstance(resume, dict) and notice:
            st.success(notice)
        error = st.session_state.get("resume_error")
        if error:
            st.error(error)
        if isinstance(resume, dict):
            st.caption("Upload another PDF to replace this resume.")
        st.button("Clear resume", key="resume-clear", on_click=clear_resume)
    resume = st.session_state.get("resume")
    if isinstance(resume, dict) and resume.get("text"):
        return resume
    return None


def _accept_upload(uploaded) -> None:
    if uploaded is None:
        return
    name = uploaded.name or "resume.pdf"
    data = uploaded.getvalue()
    if not name.lower().endswith(".pdf"):
        _reject_upload(data, "This file is not a PDF.")
        return
    if len(data) > MAX_RESUME_BYTES:
        _reject_upload(data, "This PDF is larger than 5 MB. Upload a smaller file.")
        return
    signature = hashlib.sha256(data).hexdigest()
    if signature == st.session_state.get("resume_signature") and (
        st.session_state.get("resume") or st.session_state.get("resume_error")
    ):
        return
    st.session_state.resume = None
    st.session_state.resume_match = None
    st.session_state.resume_signature = signature
    st.session_state.resume_notice = None
    _clear_improvement_checks()
    with st.spinner("Reading the PDF."):
        body, error = authed_upload(
            f"/candidates/{st.session_state.candidate_id}/resume/extract",
            name,
            data,
        )
    if error:
        st.session_state.resume_error = error
        return
    if not isinstance(body, dict) or body.get("status") != "extracted" or not body.get("text"):
        st.session_state.resume_error = "Text could not be extracted from that PDF."
        return
    st.session_state.resume_error = None
    st.session_state.resume_notice = "The PDF was read for this session. The original file was not stored."
    st.session_state.resume = {
        "filename": body.get("filename") or name,
        "message": body.get("message") or "Text extracted.",
        "page_count": body.get("page_count"),
        "character_count": body.get("character_count"),
        "text": body.get("text"),
        "health": body.get("health"),
    }


def _reject_upload(data: bytes, message: str) -> None:
    st.session_state.resume = None
    st.session_state.resume_match = None
    st.session_state.resume_signature = hashlib.sha256(data).hexdigest()
    st.session_state.resume_error = message
    st.session_state.resume_notice = None
    _clear_improvement_checks()


def _clear_improvement_checks() -> None:
    for key in list(st.session_state.keys()):
        if str(key).startswith("resume-improve-"):
            del st.session_state[key]


def _render_file_status(resume: dict) -> None:
    filename = html.escape(str(resume.get("filename") or "resume.pdf"))
    message = html.escape(str(resume.get("message") or "Text extracted."))
    pages = resume.get("page_count")
    characters = resume.get("character_count")
    detail = message
    if isinstance(pages, int) and isinstance(characters, int):
        detail = f"{message} {pages} pages, {characters} characters."
    st.markdown(
        (
            "<p class='section-label'>Uploaded file</p>"
            f"<p class='match-title resume-filename'>{filename}</p>"
            f"<p class='status-line'>{detail}</p>"
        ),
        unsafe_allow_html=True,
    )


def _render_health_summary(health: dict) -> None:
    label, tone = _health_label(health.get("score"))
    score = health.get("score")
    passed = health.get("passed")
    total = health.get("total")
    with st.container(border=True):
        st.markdown(
            (
                "<p class='section-label'>Resume health</p>"
                f"<p class='resume-health-label resume-health-{tone}'>{html.escape(label)}</p>"
                "<p class='hero-lead resume-note'>Checklist completion only. "
                "It does not mean the resume will pass every applicant tracking system.</p>"
            ),
            unsafe_allow_html=True,
        )
        if isinstance(score, int):
            st.markdown(f"<p class='resume-percent'>{score}%</p>", unsafe_allow_html=True)
        if isinstance(passed, int) and isinstance(total, int):
            st.markdown(f"{passed} of {total} checks passed")
    _render_review_groups(health)
    with st.expander("How is resume health calculated?"):
        st.markdown(html.escape(str(health.get("formula") or "The checklist explanation was not returned.")))


def _health_label(score) -> tuple[str, str]:
    """A plain label for the existing percentage. The percentage itself is unchanged."""
    if not isinstance(score, int):
        return "Health check unavailable", "attention"
    if score >= 75:
        return "Looking good", "good"
    if score >= 50:
        return "Needs a little improvement", "mid"
    return "Needs attention", "attention"


_FRIENDLY_CHECKS = {
    "summary": "Add or improve my professional summary.",
    "projects": "Make my project descriptions clearer.",
    "quantified": "Include measurable achievements where truthful.",
    "skills": "Highlight relevant skills.",
    "education": "Review my education and project details.",
    "experience": "Make my work experience clearer.",
    "contact": "Add contact information I am willing to share.",
    "readable": "Upload a text-based PDF if this file was hard to read.",
}


def _render_review_groups(health: dict) -> None:
    checks = [check for check in health.get("checks") or [] if isinstance(check, dict)]
    if not checks:
        st.markdown(
            "<p class='hero-lead'>No checklist items were returned.</p>",
            unsafe_allow_html=True,
        )
    else:
        present = [check for check in checks if check.get("status") == "found"]
        improve = [check for check in checks if check.get("status") != "found"]
        if present:
            with st.container(border=True):
                _review_group("Present in your resume", present, "found", "")
        if improve:
            with st.container(border=True):
                _review_group("Could be improved", improve, "missing", "")
    suggestions = [str(item) for item in health.get("suggestions") or [] if str(item).strip()]
    if suggestions:
        with st.container(border=True):
            _bullet_section("Recommendations", suggestions)


def _review_group(title: str, checks: list[dict], kind: str, empty: str) -> None:
    st.markdown(f"<p class='section-label'>{html.escape(title)}</p>", unsafe_allow_html=True)
    if not checks:
        st.markdown(f"<p class='hero-lead'>{html.escape(empty)}</p>", unsafe_allow_html=True)
        return
    cards = []
    for check in checks:
        status = "found" if kind == "found" else str(check.get("status") or "missing")
        state = {"found": "Present", "incomplete": "Could be clearer"}.get(status, "Not found")
        mark = "✓" if kind == "found" else "•"
        cards.append(
            "<div class='resume-check resume-"
            + html.escape(status)
            + "'>"
            + f"<p class='section-label'><span class='resume-mark'>{mark}</span>"
            + f"{html.escape(str(check.get('label') or 'Check'))}</p>"
            + f"<p class='resume-state'>{state}</p>"
            + f"<p class='hero-lead'>{html.escape(str(check.get('detail') or ''))}</p>"
            + "</div>"
        )
    st.markdown(f"<div class='resume-checks'>{''.join(cards)}</div>", unsafe_allow_html=True)


def _improvement_items(health: dict) -> list[str]:
    """Checklist lines that come from missing checks or the returned suggestions."""
    labels: list[str] = []
    seen: set[str] = set()

    def add(label: str) -> None:
        text = " ".join(str(label).split())
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            labels.append(text)

    for check in health.get("checks") or []:
        if not isinstance(check, dict) or check.get("status") == "found":
            continue
        friendly = _FRIENDLY_CHECKS.get(str(check.get("key") or ""))
        if friendly:
            add(friendly)
        elif check.get("suggestion"):
            add(str(check.get("suggestion")))
    for suggestion in health.get("suggestions") or []:
        add(str(suggestion))
    return labels[:8]


def _render_improvement_checklist(health: dict) -> None:
    items = _improvement_items(health)
    st.markdown("<p class='section-label'>My Resume Improvement Checklist</p>", unsafe_allow_html=True)
    if not items:
        st.markdown(
            "<p class='hero-lead'>No improvement items came from this resume.</p>",
            unsafe_allow_html=True,
        )
        return
    done = 0
    for label in items:
        key = "resume-improve-" + "".join(ch.lower() if ch.isalnum() else "-" for ch in label)[:48].strip("-")
        checked = st.checkbox(label, key=key or "resume-improve-item")
        if checked:
            done += 1
    st.markdown(
        f"<p class='status-line resume-progress'>{done} of {len(items)} improvements completed</p>",
        unsafe_allow_html=True,
    )
    st.progress(done / len(items))
    st.caption("Checking an item does not change the PDF. Update your file, then upload the revised resume.")


def _render_match() -> None:
    resume = st.session_state.get("resume")
    if not isinstance(resume, dict) or not resume.get("text"):
        resume = _render_upload()
    if not isinstance(resume, dict) or not resume.get("text"):
        empty_state(
            "Upload a resume first",
            "Job comparison uses the text extracted from your PDF.",
            "resume-match-empty",
        )
        return
    error = _load_jobs()
    jobs = st.session_state.get("job_catalog")
    if error or not isinstance(jobs, list):
        st.error(error or "The job list could not be read.")
        return
    if not jobs:
        with st.container(border=True):
            empty_state(
                "No jobs are stored yet",
                "Job comparison opens when the catalog has listings.",
                "resume-jobs-empty",
            )
        return
    labels, by_label = _job_choices(jobs)
    with st.container(border=True):
        st.markdown("<p class='section-label'>Selected job</p>", unsafe_allow_html=True)
        choice = st.selectbox("Job", labels, key="resume-job")
        selected = by_label[choice]
        _show_selected_job(selected)
        _render_relevant_skills(selected.get("required_skills"))
        if st.button("Analyze Resume for This Job", type="primary"):
            with st.spinner("Reading your resume against this job."):
                _compare(selected, str(resume.get("text") or ""))
    match = st.session_state.get("resume_match")
    if isinstance(match, dict) and match.get("job_id") == selected.get("id"):
        _render_match_result(match)


def _show_selected_job(job: dict) -> None:
    title = html.escape(str(job.get("title") or "Untitled role"))
    company = html.escape(str(job.get("company") or ""))
    location = html.escape(str(job.get("location") or ""))
    st.markdown(
        (
            f"<p class='match-title'>{title}</p>"
            f"<p class='match-company'>{company}</p>"
            f"<p class='match-location'>{location}</p>"
        ),
        unsafe_allow_html=True,
    )


def _load_jobs() -> str | None:
    if st.session_state.get("job_catalog") is not None:
        return None
    with st.spinner("Loading jobs."):
        body, error = authed_request("GET", "/jobs/")
    if error is None and isinstance(body, list):
        st.session_state.job_catalog = body
        return None
    return error or "The job list could not be read."


def _job_choices(jobs: list[dict]) -> tuple[list[str], dict[str, dict]]:
    labels: list[str] = []
    by_label: dict[str, dict] = {}
    for job in jobs:
        title = str(job.get("title") or "Untitled role")
        company = str(job.get("company") or "Company")
        label = f"{title} — {company}"
        if label in by_label:
            label = f"{label} ({job.get('id')})"
        labels.append(label)
        by_label[label] = job
    return labels, by_label


def _compare(job: dict, text: str) -> None:
    body, error = authed_request(
        "POST",
        f"/candidates/{st.session_state.candidate_id}/resume/match",
        {"job_id": job.get("id"), "text": text},
    )
    if error or not isinstance(body, dict):
        st.session_state.resume_match = None
        st.error(error or "The resume could not be compared with that job.")
        return
    st.session_state.resume_match = body


def _skill_names(values) -> list[str]:
    return [str(skill) for skill in values or [] if str(skill).strip()]


def _render_relevant_skills(values) -> None:
    names = _skill_names(values)
    if not names:
        return
    st.markdown("<p class='section-label'>Relevant skills</p>", unsafe_allow_html=True)
    st.markdown(f"<p class='hero-lead'>{html.escape(', '.join(names))}</p>", unsafe_allow_html=True)


def _render_match_result(match: dict) -> None:
    percent = match.get("coverage_percent")
    percent_text = "—" if not isinstance(percent, int) else f"{percent}%"
    found = _skill_names(match.get("found_skills"))
    missing = _skill_names(match.get("missing_skills"))
    with st.container(border=True):
        _show_selected_job(match)
        count_line = ""
        if isinstance(match.get("found_count"), int) and isinstance(match.get("required_count"), int):
            count_line = (
                f"<p class='hero-lead'>{match['found_count']} of {match['required_count']} "
                "required skills were found by exact wording.</p>"
            )
        st.markdown(
            (
                "<p class='section-label'>Required Skill Coverage</p>"
                f"<p class='resume-percent resume-metric-value'>{html.escape(percent_text)}</p>"
                "<p class='hero-lead resume-note'>Exact wording only. "
                "It does not guarantee interview selection. "
                "It is not an applicant tracking score.</p>"
                f"{count_line}"
            ),
            unsafe_allow_html=True,
        )
    if found or missing or _related_rows(match.get("related_skills")):
        with st.container(border=True):
            if found:
                st.markdown("<p class='section-label'>Exact matches</p>", unsafe_allow_html=True)
                chips(found, "exact")
            _render_related_skills(match.get("related_skills"))
            if missing:
                st.markdown("<p class='section-label'>Missing skills</p>", unsafe_allow_html=True)
                chips(missing, "missing")
    else:
        st.markdown(
            "<p class='hero-lead'>No required-skill comparison was returned.</p>",
            unsafe_allow_html=True,
        )
    strengths = [str(item) for item in match.get("strengths") or [] if str(item).strip()]
    suggestions = [str(item) for item in match.get("suggestions") or [] if str(item).strip()]
    if strengths:
        with st.container(border=True):
            _bullet_section("Your Strengths", strengths)
    if suggestions:
        with st.container(border=True):
            _bullet_section("How to Improve", suggestions)
    gaps = [str(item) for item in match.get("gaps") or [] if str(item).strip()]
    if gaps:
        with st.expander("Why these skills are listed"):
            _bullet_section("Details", gaps)
    _render_match_notes(match)


def _related_rows(related) -> list[dict]:
    rows = []
    for item in related or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("resume_skill") or "").strip() and str(item.get("required_skill") or "").strip():
            rows.append(item)
    return rows


def _render_related_skills(related) -> None:
    rows = _related_rows(related)
    if not rows:
        return
    st.markdown("<p class='section-label'>Related skills</p>", unsafe_allow_html=True)
    for item in rows:
        resume_skill = html.escape(str(item.get("resume_skill") or ""))
        required_skill = html.escape(str(item.get("required_skill") or ""))
        st.markdown(
            (
                "<p class='hero-lead resume-related'>"
                f"<span class='chip chip-semantic'>{resume_skill}</span> "
                f"is related to {required_skill}. "
                "This is not counted as the required skill."
                "</p>"
            ),
            unsafe_allow_html=True,
        )


def _render_match_notes(match: dict) -> None:
    keywords_found = _skill_names(match.get("keywords_found"))
    keywords_missing = _skill_names(match.get("keywords_missing"))
    experience = match.get("min_experience")
    formula = str(match.get("formula") or "").strip()
    has_notes = bool(keywords_found or keywords_missing or isinstance(experience, int) or formula or "semantic_used" in match)
    if not has_notes:
        return
    with st.expander("More about this comparison"):
        if keywords_found:
            st.markdown("<p class='section-label'>Words from the job description found in the resume</p>", unsafe_allow_html=True)
            chips(keywords_found, "exact")
        if keywords_missing:
            st.markdown("<p class='section-label'>Job words not found</p>", unsafe_allow_html=True)
            chips(keywords_missing, "missing")
        if isinstance(experience, int):
            st.markdown(
                f"<p class='hero-lead'>This job lists a minimum of {experience} years. "
                "That figure is not treated as something the resume proved.</p>",
                unsafe_allow_html=True,
            )
        if "semantic_used" in match:
            note = (
                "Related wording was compared using skill names only and is not part of the percentage."
                if match.get("semantic_used")
                else "The percentage uses exact wording only."
            )
            st.markdown(f"<p class='hero-lead'>{html.escape(note)}</p>", unsafe_allow_html=True)
        if formula:
            st.markdown(html.escape(formula))
        elif "formula" in match:
            st.markdown("The coverage explanation was not returned.")


def _bullet_section(title: str, items) -> None:
    rows = [str(item) for item in items or [] if str(item).strip()]
    if not rows:
        return
    body = "".join(f"<li>{html.escape(item)}</li>" for item in rows)
    st.markdown(
        f"<p class='section-label'>{html.escape(title)}</p><ul class='resume-list'>{body}</ul>",
        unsafe_allow_html=True,
    )
