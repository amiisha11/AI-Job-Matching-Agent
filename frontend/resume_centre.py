"""Resume Centre. Extraction stays in this session and the original PDF is not stored."""

import hashlib
import html

import streamlit as st

from auth_session import authed_request, authed_upload
from components import chips, empty_state, page_header, require_profile

MAX_RESUME_BYTES = 5 * 1024 * 1024

_PRIVACY = (
    "The original PDF is not saved. Extracted text is kept only in this signed-in session "
    "and is removed when you clear it or log out. The full resume is not sent to an external AI service."
)


def page_resume() -> None:
    """A guided resume check and one-job comparison. The PDF is not stored."""
    page_header(
        "Resume Centre",
        "Make your resume stronger and discover how well it fits the jobs you're interested in.",
        "Resume",
    )
    st.markdown("<div class='resume-page'></div>", unsafe_allow_html=True)
    if not require_profile():
        return
    st.markdown(f"<p class='hero-lead resume-privacy'>{html.escape(_PRIVACY)}</p>", unsafe_allow_html=True)
    choice = st.radio(
        "Choose a step",
        ["Check My Resume", "Match My Resume to a Job"],
        horizontal=True,
        key="resume-section",
    )
    if choice == "Match My Resume to a Job":
        _render_match()
    else:
        _render_health()


def _show_check() -> None:
    st.session_state["resume-section"] = "Check My Resume"


def clear_resume() -> None:
    """Remove the session resume without calling a storage API."""
    from auth_session import _clear_resume_state

    _clear_resume_state()


def _render_health() -> None:
    st.markdown(
        (
            "<p class='section-label resume-heading'>Step 1 — Upload your resume</p>"
            "<p class='hero-lead'>Upload your resume as a PDF. We'll review its content and suggest practical improvements.</p>"
        ),
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        uploaded = st.file_uploader(
            "PDF resume",
            type=["pdf"],
            key=f"resume-file-{st.session_state.get('resume_uploader', 0)}",
            help="PDF only, up to 5 MB. The file itself is not stored.",
        )
        _accept_upload(uploaded)
        resume = st.session_state.get("resume")
        if isinstance(resume, dict):
            st.caption("Upload another PDF to replace this resume.")
        st.button("Clear resume", key="resume-clear", on_click=clear_resume)
        error = st.session_state.get("resume_error")
        if error:
            st.error(error)
        if not isinstance(resume, dict):
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
    _clear_improvement_checks()
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
    st.markdown(
        (
            "<p class='section-label'>Resume health</p>"
            f"<p class='resume-health-label resume-health-{tone}'>{html.escape(label)}</p>"
            "<p class='hero-lead resume-note'>This is a checklist in this application. "
            "It does not mean the resume will pass every applicant tracking system.</p>"
        ),
        unsafe_allow_html=True,
    )
    _render_review_groups(health)
    with st.expander("How is resume health calculated?"):
        score = health.get("score")
        passed = health.get("passed")
        total = health.get("total")
        if isinstance(score, int):
            st.markdown(f"<p class='resume-percent'>{score}%</p>", unsafe_allow_html=True)
        if isinstance(passed, int) and isinstance(total, int):
            st.markdown(f"{passed} of {total} checks passed")
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
    present = [check for check in checks if check.get("status") == "found"]
    improve = [check for check in checks if check.get("status") != "found"]
    _review_group("Present in your resume", present, "found", "Nothing was detected in this resume yet.")
    _review_group(
        "Could be improved",
        improve,
        "missing",
        "Nothing here needs a change from the checks we ran.",
    )
    _bullet_section("Suggestions", health.get("suggestions"))


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
    st.markdown("<p class='section-label resume-heading'>Match My Resume to a Job</p>", unsafe_allow_html=True)
    st.button("Back to my resume", key="resume-back", on_click=_show_check)
    resume = st.session_state.get("resume")
    if not isinstance(resume, dict) or not resume.get("text"):
        with st.container(border=True):
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
        st.markdown("<p class='section-label'>Step 1 — Select a job</p>", unsafe_allow_html=True)
        choice = st.selectbox("Job", labels, key="resume-job")
        selected = by_label[choice]
        _show_selected_job(selected)
        st.markdown("<p class='section-label'>Step 2 — Analyze my resume</p>", unsafe_allow_html=True)
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


def _render_match_result(match: dict) -> None:
    percent = match.get("coverage_percent")
    percent_text = "—" if not isinstance(percent, int) else f"{percent}%"
    st.markdown("<p class='section-label'>Step 3 — Results for this job</p>", unsafe_allow_html=True)
    _show_selected_job(match)
    st.markdown(
        (
            "<p class='section-label'>Required Skill Coverage</p>"
            f"<p class='resume-percent resume-metric-value'>{html.escape(percent_text)}</p>"
            "<p class='hero-lead'>This percentage shows how many of the job's required skills we identified "
            "in your resume. It does not guarantee interview selection.</p>"
        ),
        unsafe_allow_html=True,
    )
    st.markdown("<p class='section-label'>Your Matching Skills</p>", unsafe_allow_html=True)
    chips([str(skill) for skill in match.get("found_skills") or []], "exact")
    st.markdown("<p class='section-label'>Skills to Work On</p>", unsafe_allow_html=True)
    chips([str(skill) for skill in match.get("missing_skills") or []], "missing")
    st.caption("These required skills were not found in the resume. Add one only if you have used it.")
    with st.container(border=True):
        _bullet_section("Your Strengths", match.get("strengths"))
    with st.container(border=True):
        _bullet_section("How to Improve", match.get("suggestions"))
    gaps = match.get("gaps") if isinstance(match.get("gaps"), list) else []
    if gaps:
        with st.expander("Why these skills are listed"):
            _bullet_section("Details", gaps)
    with st.expander("More about this comparison"):
        related = match.get("related_skills") if isinstance(match.get("related_skills"), list) else []
        if related:
            for item in related:
                if not isinstance(item, dict):
                    continue
                st.markdown(
                    (
                        "<p class='hero-lead'>"
                        f"{html.escape(str(item.get('resume_skill') or ''))} is related to "
                        f"{html.escape(str(item.get('required_skill') or ''))}. "
                        "This is not counted as the required skill."
                        "</p>"
                    ),
                    unsafe_allow_html=True,
                )
        st.markdown("<p class='section-label'>Words from the job description found in the resume</p>", unsafe_allow_html=True)
        chips([str(word) for word in match.get("keywords_found") or []], "exact")
        st.markdown("<p class='section-label'>Job words not found</p>", unsafe_allow_html=True)
        chips([str(word) for word in match.get("keywords_missing") or []], "missing")
        experience = match.get("min_experience")
        if isinstance(experience, int):
            st.markdown(
                f"<p class='hero-lead'>This job lists a minimum of {experience} years. "
                "That figure is not treated as something the resume proved.</p>",
                unsafe_allow_html=True,
            )
        note = (
            "Related wording was compared using skill names only and is not part of the percentage."
            if match.get("semantic_used")
            else "The percentage uses exact wording only."
        )
        st.markdown(f"<p class='hero-lead'>{html.escape(note)}</p>", unsafe_allow_html=True)
        st.markdown(html.escape(str(match.get("formula") or "The coverage explanation was not returned.")))


def _bullet_section(title: str, items) -> None:
    rows = [str(item) for item in items or [] if str(item).strip()]
    body = "".join(f"<li>{html.escape(item)}</li>" for item in rows)
    content = f"<ul class='resume-list'>{body}</ul>" if body else "<p class='hero-lead'>None identified from the text.</p>"
    st.markdown(
        f"<p class='section-label'>{html.escape(title)}</p>{content}",
        unsafe_allow_html=True,
    )
