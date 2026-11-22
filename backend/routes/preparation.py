"""Preparation journal routes. Every path requires the signed-in candidate."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from database import get_db
from deps import ensure_owner, get_current_candidate
from models import Candidate
from routes.jobs import get_job_or_404
from services.preparation import add_task, ensure_plan, remove_task, save_journal, set_task
from services.preparation_repo import SqlPreparationRepo

router = APIRouter(tags=["preparation"])


class JournalUpdate(BaseModel):
    """Notes and the candidate's own next action."""

    notes: str = ""
    next_action: str = ""

    @field_validator("notes", "next_action")
    @classmethod
    def keep_text(cls, value: str) -> str:
        return value if isinstance(value, str) else ""


class TaskCreate(BaseModel):
    """A task the candidate writes."""

    label: str = Field(min_length=1, max_length=240)


class TaskUpdate(BaseModel):
    """Check or uncheck one task."""

    completed: bool


def _repo(db: Session) -> SqlPreparationRepo:
    return SqlPreparationRepo(db)


def _raise_for_result(result) -> dict:
    if not result.ok or result.plan is None:
        raise HTTPException(status_code=result.status, detail=result.message)
    return result.plan


@router.get("/candidates/{candidate_id}/jobs/{job_id}/preparation")
def read_preparation(
    candidate_id: int,
    job_id: int,
    current: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> dict:
    """Return this candidate's plan for one job. The starter list is stored on the first open."""
    ensure_owner(current, candidate_id)
    job = get_job_or_404(db, job_id)
    result = ensure_plan(_repo(db), current.id, job.id, job.title, list(job.required_skills or []))
    return _raise_for_result(result)


@router.put("/candidates/{candidate_id}/jobs/{job_id}/preparation")
def update_journal(
    candidate_id: int,
    job_id: int,
    payload: JournalUpdate,
    current: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> dict:
    """Save notes and the next action for this candidate and job."""
    ensure_owner(current, candidate_id)
    get_job_or_404(db, job_id)
    result = save_journal(_repo(db), current.id, job_id, payload.notes, payload.next_action)
    return _raise_for_result(result)


@router.post(
    "/candidates/{candidate_id}/jobs/{job_id}/preparation/tasks",
    status_code=status.HTTP_201_CREATED,
)
def create_task(
    candidate_id: int,
    job_id: int,
    payload: TaskCreate,
    current: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> dict:
    """Add a personal task to this job's plan."""
    ensure_owner(current, candidate_id)
    get_job_or_404(db, job_id)
    result = add_task(_repo(db), current.id, job_id, payload.label)
    return _raise_for_result(result)


@router.patch("/candidates/{candidate_id}/jobs/{job_id}/preparation/tasks/{task_id}")
def update_task(
    candidate_id: int,
    job_id: int,
    task_id: int,
    payload: TaskUpdate,
    current: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> dict:
    """Mark one of this candidate's tasks complete or incomplete."""
    ensure_owner(current, candidate_id)
    get_job_or_404(db, job_id)
    result = set_task(_repo(db), current.id, job_id, task_id, payload.completed)
    return _raise_for_result(result)


@router.delete("/candidates/{candidate_id}/jobs/{job_id}/preparation/tasks/{task_id}")
def delete_task(
    candidate_id: int,
    job_id: int,
    task_id: int,
    current: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> dict:
    """Delete a task this candidate added."""
    ensure_owner(current, candidate_id)
    get_job_or_404(db, job_id)
    result = remove_task(_repo(db), current.id, job_id, task_id)
    return _raise_for_result(result)
