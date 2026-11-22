"""Candidate profile routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from deps import ensure_owner, get_current_candidate
from models import Candidate, Job
from routes.jobs import JobRead
from services.ai_service import embed_skill_strings, explain_matches
from services.matching import eligible_for_ranking, score_with_skill_vectors, skill_texts_for_embedding
from settings import get_skill_similarity_threshold

router = APIRouter(prefix="/candidates", tags=["candidates"])


class CandidateUpdate(BaseModel):
    """Fields a signed-in user can change. Email stays the login address."""

    name: str = Field(min_length=1, max_length=200)
    email: str | None = None
    education: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    specialization: str | None = None
    institution: str | None = None
    graduation_year: int | None = None
    skills: list[str] = Field(default_factory=list)
    preferred_roles: list[str] = Field(default_factory=list)
    preferred_industries: list[str] = Field(default_factory=list)
    preferred_locations: list[str] = Field(default_factory=list)
    preferred_countries: list[str] = Field(default_factory=list)
    remote_preference: str | None = None
    years_experience: int = Field(default=0, ge=0)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Name cannot be blank.")
        return cleaned

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().lower()

    @field_validator("education", "degree", "field_of_study", "specialization", "institution")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        return cleaned or None

    @field_validator("graduation_year")
    @classmethod
    def check_graduation_year(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value < 1950 or value > 2035:
            raise ValueError("Graduation year must be between 1950 and 2035.")
        return value

    @field_validator("remote_preference")
    @classmethod
    def check_remote_preference(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().casefold()
        if not cleaned or cleaned == "not specified":
            return None
        if cleaned not in {"remote", "hybrid", "onsite"}:
            raise ValueError("Remote preference must be remote, hybrid, or onsite.")
        return cleaned

    @field_validator(
        "skills",
        "preferred_roles",
        "preferred_industries",
        "preferred_locations",
        "preferred_countries",
    )
    @classmethod
    def clean_items(cls, values: list[str]) -> list[str]:
        kept: list[str] = []
        seen: set[str] = set()
        for item in values:
            cleaned = " ".join(str(item).split())
            key = cleaned.casefold()
            if not cleaned or key in seen:
                continue
            if len(cleaned) > 80:
                raise ValueError("Each entry must be 80 characters or fewer.")
            seen.add(key)
            kept.append(cleaned)
        return kept


class CandidateRead(BaseModel):
    """Profile returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    education: str | None
    degree: str | None = None
    field_of_study: str | None = None
    specialization: str | None = None
    institution: str | None = None
    graduation_year: int | None = None
    skills: list[str]
    preferred_roles: list[str]
    preferred_industries: list[str] = Field(default_factory=list)
    preferred_locations: list[str]
    preferred_countries: list[str] = Field(default_factory=list)
    remote_preference: str | None = None
    years_experience: int


class SemanticMatchRead(BaseModel):
    """One required skill that is related to one unused candidate skill."""

    required_skill: str
    candidate_skill: str
    similarity: float


class MatchRead(BaseModel):
    """One scored job. The numbers come from the fixed formula, not from an AI model."""

    job: JobRead
    total_score: float
    skill_score: float
    role_score: float
    location_score: float
    matched_skills: list[str]
    semantic_matches: list[SemanticMatchRead]
    missing_skills: list[str]
    explanation: str


def get_candidate_or_404(db: Session, candidate_id: int) -> Candidate:
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found.")
    return candidate


@router.post("/", response_model=CandidateRead, status_code=status.HTTP_201_CREATED)
def create_candidate() -> Candidate:
    """Profiles are created from Sign Up so every account has a password."""
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Create an account from Sign Up.",
    )


@router.patch("/{candidate_id}", response_model=CandidateRead)
def update_candidate(
    candidate_id: int,
    payload: CandidateUpdate,
    current: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> Candidate:
    """Update the signed-in profile. The login email cannot be changed here."""
    ensure_owner(current, candidate_id)
    changes = payload.model_dump()
    incoming_email = changes.pop("email", None)
    if incoming_email and incoming_email != current.email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email stays the address you used to sign up.",
        )
    for field, value in changes.items():
        setattr(current, field, value)
    db.commit()
    db.refresh(current)
    return current


@router.get("/{candidate_id}", response_model=CandidateRead)
def read_candidate(
    candidate_id: int,
    current: Candidate = Depends(get_current_candidate),
) -> Candidate:
    """Return the signed-in profile."""
    ensure_owner(current, candidate_id)
    return current


@router.get("/{candidate_id}/matches", response_model=list[MatchRead])
def match_candidate(
    candidate_id: int,
    current: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db),
) -> list[MatchRead]:
    """Score every job for the signed-in candidate, highest score first."""
    ensure_owner(current, candidate_id)
    candidate = current
    jobs = [job for job in db.scalars(select(Job).order_by(Job.id)) if eligible_for_ranking(job)]
    vectors = embed_skill_strings(skill_texts_for_embedding(candidate, jobs))
    threshold = get_skill_similarity_threshold()
    scored = [(job, score_with_skill_vectors(candidate, job, vectors, threshold)) for job in jobs]
    scored.sort(key=lambda item: (-item[1].total_score, item[0].id))
    explanations = explain_matches(candidate, scored)
    return [
        MatchRead(
            job=JobRead.model_validate(job),
            total_score=score.total_score,
            skill_score=score.skill_score,
            role_score=score.role_score,
            location_score=score.location_score,
            matched_skills=score.matched_skills,
            semantic_matches=[
                SemanticMatchRead(
                    required_skill=item.required_skill,
                    candidate_skill=item.candidate_skill,
                    similarity=item.similarity,
                )
                for item in score.semantic_matches
            ],
            missing_skills=score.missing_skills,
            explanation=explanation,
        )
        for (job, score), explanation in zip(scored, explanations, strict=True)
    ]
