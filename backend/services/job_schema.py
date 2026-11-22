"""Additive SQL for Adzuna source columns.

These statements add columns and one unique index. They do not delete rows,
change sample job text, or write listings.
"""

from sqlalchemy import text

JOB_SOURCE_STATEMENTS = (
    "ALTER TABLE jobs ALTER COLUMN title TYPE VARCHAR(500)",
    "ALTER TABLE jobs ALTER COLUMN company TYPE VARCHAR(500)",
    "ALTER TABLE jobs ALTER COLUMN location TYPE VARCHAR(500)",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS source VARCHAR(40)",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS external_job_id VARCHAR(80)",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS source_country VARCHAR(2)",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS source_url TEXT",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS posted_at TIMESTAMPTZ",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS last_synced_at TIMESTAMPTZ",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS is_matchable BOOLEAN NOT NULL DEFAULT TRUE",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS matchability_status VARCHAR(20) NOT NULL DEFAULT 'matchable'",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS matchability_reason TEXT",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS description_is_snippet BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS requirements_available BOOLEAN NOT NULL DEFAULT TRUE",
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_jobs_source_listing
    ON jobs (source, source_country, external_job_id)
    WHERE external_job_id IS NOT NULL
    """,
)


# Prepared for a later migration. These statements are not applied by the
# current job-source migration and this module does not run them.
JOB_CATEGORY_STATEMENTS = (
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS category_label VARCHAR(200)",
    "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS category_tag VARCHAR(80)",
    """
    CREATE TABLE IF NOT EXISTS provider_categories (
        country VARCHAR(2) NOT NULL,
        tag VARCHAR(80) NOT NULL,
        label VARCHAR(200) NOT NULL,
        PRIMARY KEY (country, tag)
    )
    """,
)


def apply_job_source_statements(connection) -> None:
    """Run the column and index statements on an open connection."""
    for statement in JOB_SOURCE_STATEMENTS:
        connection.execute(text(statement))
