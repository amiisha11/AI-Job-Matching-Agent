"""Display helpers for the Discover Jobs preparation journal.

Progress numbers come from the API. This module does not score jobs and does
not invent tasks.
"""


def limited_skills(skills, limit: int = 3) -> tuple[list[str], int]:
    """Keep a short chip list. The full list stays available in the job details."""
    cleaned = [" ".join(str(item).split()) for item in (skills or []) if str(item).strip()]
    shown = cleaned[:limit]
    return shown, len(cleaned) - len(shown)


def progress_lines(progress: dict | None) -> tuple[str, str, bool]:
    """Turn the API progress object into the two lines shown on the plan."""
    progress = progress or {}
    completed = int(progress.get("completed") or 0)
    total = int(progress.get("total") or 0)
    remaining = progress.get("remaining")
    if remaining is None:
        remaining = total - completed
    finished = bool(progress.get("finished")) and total > 0 and completed >= total
    return (
        f"{completed} / {total} tasks",
        f"{completed} completed · {int(remaining)} remaining",
        finished,
    )
