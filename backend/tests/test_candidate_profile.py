"""Profile update, isolation, and migration checks. Uses SQLite, not Supabase."""

import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from migrate_candidate_profile import CANDIDATE_PROFILE_STATEMENTS
from models import Base, Candidate
from routes.candidates import CandidateUpdate, update_candidate
from services.matching import score_job


def test_profile_update_rejects_duplicates_and_invalid_years():
    cleaned = CandidateUpdate(
        name=" Ada ",
        skills=[" Python ", "python", "SQL"],
        preferred_roles=["Analyst", " analyst "],
        preferred_industries=["it-jobs", "IT-jobs"],
        preferred_locations=["London", " london "],
        preferred_countries=["in", "IN"],
        remote_preference="Remote",
        graduation_year=2020,
    )
    assert cleaned.skills == ["Python", "SQL"]
    assert cleaned.preferred_roles == ["Analyst"]
    assert cleaned.preferred_industries == ["it-jobs"]
    assert cleaned.preferred_locations == ["London"]
    assert cleaned.preferred_countries == ["in"]
    assert cleaned.remote_preference == "remote"
    with pytest.raises(ValidationError):
        CandidateUpdate(name="Ada", graduation_year=1800)
    with pytest.raises(ValidationError):
        CandidateUpdate(name="Ada", remote_preference="anywhere")


def test_update_preserves_the_other_candidate_and_existing_skills():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    ada = Candidate(
        name="Ada",
        email="ada@example.com",
        education="Mathematics",
        skills=["Python"],
        preferred_roles=["Data Analyst"],
        preferred_locations=["London"],
        years_experience=3,
    )
    grace = Candidate(
        name="Grace",
        email="grace@example.com",
        education="Physics",
        skills=["COBOL"],
        preferred_roles=["Engineer"],
        preferred_locations=["Boston"],
        years_experience=5,
    )
    db.add_all([ada, grace])
    db.commit()
    payload = CandidateUpdate(
        name="Ada Lovelace",
        education="Mathematics",
        degree="B.Sc.",
        skills=["Python", " python ", "SQL"],
        preferred_roles=["Data Analyst"],
        preferred_industries=["legal-jobs"],
        preferred_locations=["London"],
        preferred_countries=["gb"],
        remote_preference="hybrid",
        years_experience=3,
    )
    updated = update_candidate(ada.id, payload, ada, db)
    assert updated.skills == ["Python", "SQL"]
    assert updated.education == "Mathematics"
    assert updated.degree == "B.Sc."
    assert updated.preferred_industries == ["legal-jobs"]
    assert updated.preferred_countries == ["gb"]
    assert grace.skills == ["COBOL"]
    assert grace.education == "Physics"
    with pytest.raises(HTTPException) as denied:
        update_candidate(grace.id, payload, ada, db)
    assert denied.value.status_code == 403
    assert grace.skills == ["COBOL"]
    db.close()


def test_industry_preferences_do_not_change_the_match_score():
    class Person:
        skills = ["Python"]
        preferred_roles = ["Data Analyst"]
        preferred_locations = ["London"]

    class Listing:
        title = "Data Analyst"
        location = "London"
        required_skills = ["Python"]
        is_matchable = True
        requirements_available = True

    before = score_job(Person(), Listing())
    Person.preferred_industries = ["it-jobs"]
    Person.preferred_countries = ["in"]
    Person.remote_preference = "remote"
    after = score_job(Person(), Listing())
    assert before.skill_score == 70
    assert before.role_score == 20
    assert before.location_score == 10
    assert before.total_score == 100
    assert after == before


def test_profile_migration_only_adds_columns():
    sql = "\n".join(CANDIDATE_PROFILE_STATEMENTS).upper()
    assert "DROP " not in sql
    assert "DELETE " not in sql
    assert "TRUNCATE" not in sql
    assert "ADD COLUMN IF NOT EXISTS DEGREE" in sql
    assert "ADD COLUMN IF NOT EXISTS PREFERRED_INDUSTRIES" in sql
    assert "ADD COLUMN IF NOT EXISTS PREFERRED_COUNTRIES" in sql
    assert "ADD COLUMN IF NOT EXISTS REMOTE_PREFERENCE" in sql
