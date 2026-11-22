"""Resume extraction and comparison. Synthetic text only, and no database."""

import io
import logging
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pypdf import PdfReader, PdfWriter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from deps import get_auth_repo, get_current_candidate, get_db
from routes.resume import router
from services.resume_health import HEALTH_FORMULA, assess_resume
from services.resume_match import COVERAGE_FORMULA, match_resume_to_job
from services.resume_pdf import (
    MAX_RESUME_BYTES,
    NO_TEXT_MESSAGE,
    PASSWORD_MESSAGE,
    extract_pdf,
)

EMAIL = "ada.example@example.com"
FULL_RESUME = f"""
Example Candidate
{EMAIL}
+1 415 555 0134

Professional summary
Analyst who builds reports and reviews data quality for operations teams across weekly cycles.

Skills
Python, SQL, Excel

Work experience
Improved report delivery by 20% for the finance team.
Built a SQL pipeline used by 12 analysts and documented the refresh steps.

Education
B.Tech in Computer Science, Example University

Projects
Built a dashboard project using Python and SQL to track weekly orders for the operations group.
"""
PARTIAL_RESUME = (
    "Work experience\n"
    + ("Helped the support desk and wrote notes for the next shift. " * 12)
    + "\nEducation\nStudied commerce at a local college.\n"
)


def pdf_with_text(text: str) -> bytes:
    """A small text PDF. The words are synthetic."""
    safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 72 120 Td ({safe}) Tj ET".encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Count 1 /Kids [3 0 R] >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 500 200] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    return _pdf(objects)


def pdf_without_text() -> bytes:
    """A painted square and no text operators, standing in for a scan or image."""
    stream = b"0 0 0 rg 10 10 80 80 re f"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Count 1 /Kids [3 0 R] >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
    ]
    return _pdf(objects)


def _pdf(objects: list[bytes]) -> bytes:
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out.extend(f"{index} 0 obj\n".encode())
        out.extend(body)
        out.extend(b"\nendobj\n")
    xref = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    out.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        out.extend(f"{offset:010d} 00000 n \n".encode())
    out.extend(
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(out)


def encrypted_pdf() -> bytes:
    writer = PdfWriter()
    writer.append(PdfReader(io.BytesIO(pdf_with_text("Python should stay locked"))))
    writer.encrypt("secret-pass")
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def empty_pdf() -> bytes:
    buffer = io.BytesIO()
    PdfWriter().write(buffer)
    return buffer.getvalue()


def test_valid_pdf_extracts_text_and_does_not_echo_contact_in_the_check():
    result = extract_pdf(pdf_with_text("Skills Python SQL"), "reports/synthetic.pdf")
    assert result.ok
    assert result.filename == "synthetic.pdf"
    assert "Python" in result.text
    assert result.character_count == len(result.text)
    assert result.health["total"] == 8
    assert EMAIL not in str(result.health)


def test_invalid_empty_corrupt_password_and_image_pdfs_fail_clearly():
    assert extract_pdf(b"hello", "notes.txt").message == "This file is not a PDF."
    assert extract_pdf(b"%PDF-1.4 synthetic", "notes.txt").message == "This file is not a PDF."
    assert extract_pdf(b"", "resume.pdf").message == "This file is empty."
    assert extract_pdf(b"%PDF" + b"x" * MAX_RESUME_BYTES, "resume.pdf").message.startswith("This PDF is larger")
    assert extract_pdf(b"%PDF-1.4\nbroken", "resume.pdf").message == "This PDF could not be read. It may be corrupted."
    assert extract_pdf(empty_pdf(), "resume.pdf").message == "This PDF is empty."
    assert extract_pdf(encrypted_pdf(), "resume.pdf").message == PASSWORD_MESSAGE
    image = extract_pdf(pdf_without_text(), "scan.pdf")
    assert image.message == NO_TEXT_MESSAGE
    assert image.text == ""
    assert image.ok is False


def test_corrupt_pdf_log_does_not_include_the_file_marker(caplog):
    marker = "PRIVATE-MARKER-do-not-log"
    with caplog.at_level(logging.WARNING):
        extract_pdf(f"%PDF-1.4\n{marker}".encode(), "resume.pdf")
    assert marker not in caplog.text


def test_health_uses_eight_checks_and_explains_optional_sections():
    health = assess_resume(FULL_RESUME)
    assert health["score"] == 100
    assert health["passed"] == 8
    assert health["formula"] == HEALTH_FORMULA
    assert "applicant tracking" in health["formula"]
    assert EMAIL not in str(health["checks"])

    partial = assess_resume(PARTIAL_RESUME)
    by_key = {check["key"]: check for check in partial["checks"]}
    assert by_key["contact"]["status"] == "missing"
    assert by_key["summary"]["status"] == "missing"
    assert by_key["skills"]["status"] == "missing"
    assert by_key["experience"]["passed"] is True
    assert by_key["education"]["passed"] is True
    assert by_key["projects"]["status"] == "missing"
    assert "does not apply to every background" in by_key["projects"]["detail"] or "Leave it out" in by_key["projects"]["detail"]
    assert by_key["quantified"]["status"] == "missing"
    assert "not automatically unsuitable" in by_key["quantified"]["detail"]
    assert partial["score"] == (100 * partial["passed"] + 4) // 8
    assert all(EMAIL not in check["detail"] for check in partial["checks"])


def test_coverage_counts_exact_skills_and_does_not_invent_missing_ones():
    job = SimpleNamespace(
        id=11,
        title="Data Analyst",
        company="Northwind",
        location="Remote",
        description="Prepare dashboards and analyze operational data.",
        required_skills=["Python", "SQL", "Tableau"],
        min_experience=2,
    )
    result = match_resume_to_job(FULL_RESUME, job)
    assert result["found_skills"] == ["Python", "SQL"]
    assert result["missing_skills"] == ["Tableau"]
    assert result["coverage_percent"] == 67
    assert result["found_count"] == 2
    assert result["required_count"] == 3
    assert result["formula"] == COVERAGE_FORMULA
    assert "total_score" not in result
    assert any("includes Python" in item for item in result["strengths"])
    assert any("Do not add Tableau" in item for item in result["gaps"] + result["suggestions"])
    assert "analyze" in result["keywords_found"] or "data" in result["keywords_found"]
    assert EMAIL not in str({key: value for key, value in result.items() if key != "strengths"})
    joined = " ".join(result["strengths"] + result["gaps"] + result["suggestions"])
    assert EMAIL not in joined
    assert "Add a professional summary" not in joined


def test_related_wording_is_separate_from_coverage():
    seen = []

    def embedder(skills):
        seen.extend(skills)
        return {"tableau": [1.0, 0.0], "data visualization": [0.96, 0.28]}

    text = "Skills\nData visualization\n\nWork experience\n" + ("Prepared charts for weekly reviews. " * 8)
    job = SimpleNamespace(
        id=12,
        title="Analyst",
        company="Contoso",
        location="London",
        description="Create dashboards.",
        required_skills=["Tableau"],
        min_experience=0,
    )
    result = match_resume_to_job(text, job, embedder=embedder)
    assert result["coverage_percent"] == 0
    assert result["found_skills"] == []
    assert result["semantic_used"] is True
    assert result["related_skills"][0]["required_skill"] == "Tableau"
    assert result["related_skills"][0]["resume_skill"] == "Data visualization"
    assert EMAIL not in seen
    assert all("@" not in skill and "\n" not in skill and len(skill) <= 40 for skill in seen)


def test_embeddings_are_skipped_without_a_skills_section():
    called = []
    text = "Work experience\nUsed spreadsheets.\nContact " + EMAIL
    job = SimpleNamespace(
        id=13,
        title="Analyst",
        company="Contoso",
        location="London",
        description="Analyze data.",
        required_skills=["Tableau"],
        min_experience=0,
    )
    result = match_resume_to_job(text, job, embedder=lambda skills: called.append(skills))
    assert called == []
    assert result["semantic_used"] is False
    assert result["missing_skills"] == ["Tableau"]


class ClosedRepo:
    def get_session(self, token_hash):
        return None


class JobDB:
    def __init__(self, job):
        self.job = job

    def get(self, model, ident):
        if ident == self.job.id:
            return self.job
        return None


def _client(user_id=4, job=None):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_candidate] = lambda: SimpleNamespace(id=user_id)
    if job is not None:
        app.dependency_overrides[get_db] = lambda: JobDB(job)
    return TestClient(app)


def test_extract_route_rejects_anonymous_and_other_candidates(monkeypatch):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_auth_repo] = lambda: ClosedRepo()
    anonymous = TestClient(app)
    response = anonymous.post(
        "/candidates/4/resume/extract",
        files={"file": ("synthetic.pdf", pdf_with_text("Python"), "application/pdf")},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Log in to continue."
    assert "Python" not in response.text

    forbidden = _client(user_id=4).post(
        "/candidates/8/resume/extract",
        files={"file": ("synthetic.pdf", pdf_with_text("Python"), "application/pdf")},
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"] == "You cannot open another candidate's profile."
    assert "Python" not in forbidden.text


def test_extract_and_match_routes_keep_text_out_of_other_results(monkeypatch, caplog):
    seen = []

    def embedder(skills, client=None):
        seen.extend(skills)
        return None

    monkeypatch.setattr("routes.resume.embed_skill_strings", embedder)
    job = SimpleNamespace(
        id=11,
        title="Data Analyst",
        company="Northwind",
        location="Remote",
        description="Prepare dashboards and analyze operational data.",
        required_skills=["Python", "SQL", "Tableau"],
        min_experience=1,
    )
    client = _client(job=job)
    pdf = pdf_with_text(FULL_RESUME.replace("\n", " "))
    with caplog.at_level(logging.WARNING):
        extracted = client.post(
            "/candidates/4/resume/extract",
            files={"file": ("folder/synthetic.pdf", pdf, "application/pdf")},
        )
    assert extracted.status_code == 200
    body = extracted.json()
    assert body["status"] == "extracted"
    assert body["filename"] == "synthetic.pdf"
    assert "Python" in body["text"]
    assert EMAIL not in str(body["health"])
    assert EMAIL not in caplog.text

    compared = client.post(
        "/candidates/4/resume/match",
        json={"job_id": 11, "text": FULL_RESUME},
    )
    assert compared.status_code == 200
    match = compared.json()
    assert match["coverage_percent"] == 67
    assert match["missing_skills"] == ["Tableau"]
    assert "text" not in match
    assert EMAIL not in compared.text
    assert all("@" not in skill for skill in seen)

    missing = client.post("/candidates/4/resume/match", json={"job_id": 99, "text": FULL_RESUME})
    assert missing.status_code == 404
    blocked = _client(user_id=8, job=job).post(
        "/candidates/4/resume/match",
        json={"job_id": 11, "text": FULL_RESUME},
    )
    assert blocked.status_code == 403
    assert FULL_RESUME not in blocked.text
