"""Resume checks for the signed-in candidate.

The PDF and its text are handled in memory. Nothing is written to the database
or to disk, and the full resume is not sent to Gemini.
"""

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from database import get_db
from deps import ensure_owner, get_current_candidate
from models import Candidate
from routes.jobs import get_job_or_404
from services.ai_service import embed_skill_strings
from services.resume_match import match_resume_to_job
from services.resume_pdf import MAX_RESUME_BYTES, TOO_LARGE_MESSAGE, extract_pdf

logger = logging.getLogger(__name__)
router = APIRouter(tags=["resume"])


class ResumeMatchRequest(BaseModel):
    """A job and the text already extracted in this session."""

    job_id: int = Field(gt=0)
    text: str = Field(min_length=1, max_length=100_000)

    @field_validator("text")
    @classmethod
    def require_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Upload a resume with readable text before matching a job.")
        return cleaned


def _read_limited(upload: UploadFile) -> bytes:
    """Read at most one byte past the size limit. The file is not stored."""
    chunks: list[bytes] = []
    total = 0
    while total <= MAX_RESUME_BYTES:
        block = upload.file.read(65_536)
        if not block:
            break
        chunks.append(block)
        total += len(block)
    return b"".join(chunks)


@router.post("/candidates/{candidate_id}/resume/extract")
def extract_resume(
    candidate_id: int,
    file: UploadFile = File(...),
    current: Candidate = Depends(get_current_candidate),
) -> dict:
    """Extract text for this candidate. The original PDF is discarded."""
    ensure_owner(current, candidate_id)
    data = _read_limited(file)
    if len(data) > MAX_RESUME_BYTES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=TOO_LARGE_MESSAGE)
    result = extract_pdf(data, file.filename)
    if not result.ok or result.health is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=result.message)
    return {
        "filename": result.filename,
        "status": "extracted",
        "message": result.message,
        "page_count": result.page_count,
        "character_count": result.character_count,
        "text": result.text,
        "health": result.health,
    }


@router.post("/candidates/{candidate_id}/resume/match")
def compare_resume(
    candidate_id: int,
    payload: ResumeMatchRequest,
    current: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> dict:
    """Compare session resume text with one stored job. The text is not logged."""
    ensure_owner(current, candidate_id)
    job = get_job_or_404(db, payload.job_id)
    try:
        return match_resume_to_job(payload.text, job, embedder=embed_skill_strings)
    except Exception as exc:
        logger.warning("Resume comparison failed (%s).", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The resume could not be compared with that job.",
        ) from None
