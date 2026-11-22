"""SQLAlchemy engine and request sessions.

The connection string comes from settings, which reads the root .env file.
Importing this module does not create tables.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from settings import get_database_url

engine = create_engine(get_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    """Yield a session for one request, then close it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables() -> None:
    """Create missing tables. Existing tables and rows are left in place."""
    from models import Base

    Base.metadata.create_all(bind=engine)


def ensure_auth_schema() -> None:
    """Add the password column and session table without changing existing rows."""
    from sqlalchemy import text

    from models import AuthSession, Base

    try:
        Base.metadata.create_all(bind=engine, tables=[AuthSession.__table__])
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS password_hash TEXT")
            )
    except Exception:
        raise RuntimeError("Could not prepare the authentication tables.") from None


def ensure_job_source_schema() -> None:
    """Add source columns and the sync log table. Existing job rows stay in place."""
    from models import Base, JobSyncLog
    from services.job_schema import apply_job_source_statements

    try:
        with engine.begin() as connection:
            apply_job_source_statements(connection)
        Base.metadata.create_all(bind=engine, tables=[JobSyncLog.__table__])
    except Exception:
        raise RuntimeError("Could not prepare the job source columns.") from None


def ensure_preparation_schema() -> None:
    """Create the preparation tables. Existing candidates, jobs, and saved jobs stay as they are."""
    from models import Base, PreparationPlan, PreparationTask

    try:
        Base.metadata.create_all(
            bind=engine,
            tables=[PreparationPlan.__table__, PreparationTask.__table__],
        )
    except Exception:
        raise RuntimeError("Could not prepare the preparation tables.") from None
