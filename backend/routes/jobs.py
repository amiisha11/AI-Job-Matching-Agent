"""Job listing and saved-job routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from database import get_db
from deps import ensure_owner, get_current_candidate
from models import Candidate, Job, SavedJob
from providers.jooble.client import JoobleError, search_jobs as search_jooble_jobs
from services.job_filters import JobSearch, build_filter_metadata, filter_jobs, salary_needs_currency, search_from_params

router = APIRouter(tags=["jobs"])


class JobCreate(BaseModel):
    """Fields accepted when a job is created."""

    title: str = Field(min_length=1, max_length=200)
    company: str = Field(min_length=1, max_length=200)
    location: str = Field(min_length=1, max_length=200)
    description: str | None = None
    required_skills: list[str] = Field(default_factory=list)
    min_experience: int = Field(default=0, ge=0)

    @field_validator("title", "company", "location")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("This field cannot be blank.")
        return cleaned

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("required_skills")
    @classmethod
    def clean_skills(cls, values: list[str]) -> list[str]:
        return [item.strip() for item in values if item and item.strip()]


class JobRead(BaseModel):
    """Job returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    company: str
    location: str
    description: str | None
    required_skills: list[str]
    min_experience: int
    source: str | None = None
    external_job_id: str | None = None
    source_country: str | None = None
    source_url: str | None = None
    posted_at: datetime | None = None
    is_matchable: bool = True
    matchability_status: str = "matchable"
    matchability_reason: str | None = None
    description_is_snippet: bool = False
    requirements_available: bool = True
    category_label: str | None = None
    category_tag: str | None = None


class SaveJobRequest(BaseModel):
    """Identifies which candidate is saving the job in the URL."""

    candidate_id: int = Field(gt=0)


class SavedJobRead(BaseModel):
    """A saved job, including the listing it points to."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    job_id: int
    created_at: datetime
    job: JobRead


def get_job_or_404(db: Session, job_id: int) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    return job


def get_candidate_or_404(db: Session, candidate_id: int) -> Candidate:
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found.")
    return candidate


@router.post("/jobs/", response_model=JobRead, status_code=status.HTTP_201_CREATED)
def create_job(payload: JobCreate, db: Session = Depends(get_db)) -> Job:
    """Store one job listing."""
    job = Job(**payload.model_dump())
    db.add(job)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The job could not be saved. Check that min_experience is zero or greater.",
        ) from None
    db.refresh(job)
    return job


@router.get("/jobs/filters")
def read_job_filters(db: Session = Depends(get_db)) -> dict:
    """Filter choices from the categories stored on the listings."""
    jobs = list(db.scalars(select(Job).order_by(Job.id)))
    return build_filter_metadata(jobs)


@router.get("/jobs/", response_model=list[JobRead])
def list_jobs(
    db: Session = Depends(get_db),
    q: str | None = None,
    category: str | None = None,
    country: str | None = None,
    location: str | None = None,
    workplace: str | None = None,
    employment: str | None = None,
    experience: str | None = None,
    salary_currency: str | None = None,
    salary_min: float | None = None,
    salary_max: float | None = None,
    sort: str | None = None,
) -> list[Job]:
    """Return stored listings. Filters run here so the page does not download every row again."""
    rows = list(db.scalars(select(Job).order_by(Job.id)))
    search = search_from_params(
        {
            "q": q,
            "category": category,
            "country": country,
            "location": location,
            "workplace": workplace,
            "employment": employment,
            "experience": experience,
            "salary_currency": salary_currency,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "sort": sort,
        }
    )
    if _search_is_open(search):
        return rows
    if salary_needs_currency(search):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Choose a currency before filtering by salary.",
        )
    return filter_jobs(rows, search)


@router.get("/jobs/jooble")
def read_jooble_jobs(country: str, q: str, location: str | None = None) -> dict:
    """Search one Jooble region. The stored catalogue is not changed."""
    try:
        jobs = search_jooble_jobs(country=country, keywords=q, location=location)
    except JoobleError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from None
    return {"jobs": [job.as_dict() for job in jobs], "detail": None}


@router.get("/jobs/{job_id}", response_model=JobRead)
def read_job(job_id: int, db: Session = Depends(get_db)) -> Job:
    """Return one job listing by its id."""
    return get_job_or_404(db, job_id)


@router.post("/jobs/{job_id}/save", response_model=SavedJobRead, status_code=status.HTTP_201_CREATED)
def save_job(
    job_id: int,
    payload: SaveJobRequest,
    current: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> SavedJob:
    """Save a job for the signed-in candidate. The same pair can be saved only once."""
    ensure_owner(current, payload.candidate_id)
    get_job_or_404(db, job_id)
    get_candidate_or_404(db, payload.candidate_id)

    existing = db.scalar(
        select(SavedJob).where(
            SavedJob.candidate_id == payload.candidate_id,
            SavedJob.job_id == job_id,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This job is already saved for that candidate.",
        )

    saved = SavedJob(candidate_id=payload.candidate_id, job_id=job_id)
    db.add(saved)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This job is already saved for that candidate.",
        ) from None
    db.refresh(saved)
    saved.job = get_job_or_404(db, job_id)
    return saved


@router.get("/candidates/{candidate_id}/saved-jobs", response_model=list[SavedJobRead])
def list_saved_jobs(
    candidate_id: int,
    current: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> list[SavedJob]:
    """Return the jobs the signed-in candidate has saved, newest first."""
    ensure_owner(current, candidate_id)
    get_candidate_or_404(db, candidate_id)
    saved = db.scalars(
        select(SavedJob)
        .where(SavedJob.candidate_id == candidate_id)
        .options(selectinload(SavedJob.job))
        .order_by(SavedJob.created_at.desc())
    )
    return list(saved)


def _search_is_open(search: JobSearch) -> bool:
    return not any(
        (
            search.text,
            search.category,
            search.country,
            search.location,
            search.workplace,
            search.employment,
            search.experience,
            search.salary_currency,
            search.sort,
        )
    ) and search.salary_min is None and search.salary_max is None
