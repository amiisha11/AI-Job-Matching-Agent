"""SQLAlchemy tables for candidates, jobs, and saved jobs.

Skills and preferences are PostgreSQL text arrays so overlap checks stay simple.
"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""


SkillList = ARRAY(Text).with_variant(JSON(), "sqlite")


class Candidate(Base):
    """A job seeker. Email is the identity for this version of the app."""

    __tablename__ = "candidates"
    __table_args__ = (CheckConstraint("years_experience >= 0", name="ck_candidates_years_experience"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    education: Mapped[str | None] = mapped_column(Text)
    degree: Mapped[str | None] = mapped_column(Text)
    field_of_study: Mapped[str | None] = mapped_column(Text)
    specialization: Mapped[str | None] = mapped_column(Text)
    institution: Mapped[str | None] = mapped_column(Text)
    graduation_year: Mapped[int | None] = mapped_column(Integer)
    skills: Mapped[list[str]] = mapped_column(SkillList, nullable=False, default=list)
    preferred_roles: Mapped[list[str]] = mapped_column(SkillList, nullable=False, default=list)
    preferred_industries: Mapped[list[str]] = mapped_column(SkillList, nullable=False, default=list)
    preferred_locations: Mapped[list[str]] = mapped_column(SkillList, nullable=False, default=list)
    preferred_countries: Mapped[list[str]] = mapped_column(SkillList, nullable=False, default=list)
    remote_preference: Mapped[str | None] = mapped_column(String(20))
    years_experience: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    password_hash: Mapped[str | None] = mapped_column(Text)

    saved_jobs: Mapped[list["SavedJob"]] = relationship(
        back_populates="candidate",
        cascade="all, delete-orphan",
    )
    preparation_plans: Mapped[list["PreparationPlan"]] = relationship(
        back_populates="candidate",
        cascade="all, delete-orphan",
    )


class Job(Base):
    """A job listing. Sample rows leave the source columns empty."""

    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint("min_experience >= 0", name="ck_jobs_min_experience"),
        Index(
            "uq_jobs_source_listing",
            "source",
            "source_country",
            "external_job_id",
            unique=True,
            postgresql_where=text("external_job_id IS NOT NULL"),
            sqlite_where=text("external_job_id IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    company: Mapped[str] = mapped_column(String(500), nullable=False)
    location: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    required_skills: Mapped[list[str]] = mapped_column(SkillList, nullable=False, default=list)
    min_experience: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str | None] = mapped_column(String(40))
    external_job_id: Mapped[str | None] = mapped_column(String(80))
    source_country: Mapped[str | None] = mapped_column(String(2))
    source_url: Mapped[str | None] = mapped_column(Text)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    is_matchable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    matchability_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="matchable",
        server_default="matchable",
    )
    matchability_reason: Mapped[str | None] = mapped_column(Text)
    description_is_snippet: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    requirements_available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    saved_jobs: Mapped[list["SavedJob"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
    )
    preparation_plans: Mapped[list["PreparationPlan"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
    )


class SavedJob(Base):
    """One saved job for one candidate. The same pair cannot be saved twice."""

    __tablename__ = "saved_jobs"
    __table_args__ = (UniqueConstraint("candidate_id", "job_id", name="uq_saved_jobs_candidate_job"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    candidate: Mapped[Candidate] = relationship(back_populates="saved_jobs")
    job: Mapped[Job] = relationship(back_populates="saved_jobs")


class PreparationPlan(Base):
    """One candidate's notes and tasks for one job. Other candidates cannot share it."""

    __tablename__ = "preparation_plans"
    __table_args__ = (
        UniqueConstraint("candidate_id", "job_id", name="uq_preparation_candidate_job"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    next_action: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    candidate: Mapped[Candidate] = relationship(back_populates="preparation_plans")
    job: Mapped[Job] = relationship(back_populates="preparation_plans")
    tasks: Mapped[list["PreparationTask"]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="PreparationTask.position",
    )


class PreparationTask(Base):
    """A checklist row. Starter tasks stay on the plan; only added tasks can be deleted."""

    __tablename__ = "preparation_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("preparation_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label: Mapped[str] = mapped_column(Text, nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    is_custom: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    plan: Mapped[PreparationPlan] = relationship(back_populates="tasks")


class JobSyncLog(Base):
    """One Adzuna import attempt. Credentials are never stored here."""

    __tablename__ = "job_sync_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False)
    search_query: Mapped[str] = mapped_column(String(200), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fetched_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    inserted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)


class ClaimToken(Base):
    """One administrator-issued claim code. Only the hash is stored."""

    __tablename__ = "claim_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ClaimGuard(Base):
    """Failed claim attempts for one email. This does not block password login."""

    __tablename__ = "claim_guards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EmailSetupOTP(Base):
    """One emailed setup code. Only the HMAC is stored."""

    __tablename__ = "email_setup_otps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    otp_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class OtpSend(Base):
    """One OTP request, including requests that did not send a message."""

    __tablename__ = "otp_sends"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    client_ip: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class OtpGuard(Base):
    """Failed OTP checks for one email. Password login does not read this table."""

    __tablename__ = "otp_guards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuthSession(Base):
    """A login session. Only the hash of the token is stored."""

    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
