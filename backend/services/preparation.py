"""Preparation plans for one candidate and one job.

These functions decide what to store. They do not open a database connection.
Starter tasks are suggestions for the candidate, not a description of an
employer's hiring process.
"""

from dataclasses import dataclass

from services.auth_service import owner_conflict

MAX_TASKS = 40
MAX_LABEL = 240
MAX_NOTES = 4000
MAX_ACTION = 240


@dataclass
class PrepResult:
    """A preparation decision. The plan is public data, with no other candidate mixed in."""

    ok: bool
    status: int
    message: str
    plan: dict | None = None


def access_error(current_id: int, requested_id: int) -> str | None:
    """Refuse a request for another candidate's preparation plan."""
    return owner_conflict(current_id, requested_id)


def starter_labels(title: str, skills: list[str] | None) -> list[str]:
    """Build the first checklist from the listing's own title and skills."""
    role = " ".join(str(title or "").split()) or "this role"
    cleaned = [" ".join(str(skill).split()) for skill in (skills or []) if str(skill).strip()]
    skill_text = ", ".join(cleaned[:4])
    extra = len(cleaned) - 4
    if extra > 0:
        skill_text = f"{skill_text}, and {extra} more"
    skill_suffix = f": {skill_text}" if skill_text else ""
    return [
        f"Read the complete job description for {role}.",
        f"Review the required skills{skill_suffix}.",
        f"Identify skills I need to improve{skill_suffix}.",
        f"Prepare projects that show the work I can do as {role}.",
        f"Update my resume for the {role} role.",
        f"Prepare interview questions for {role}.",
        f"Research the company that posted {role}.",
    ]


def progress_summary(tasks: list[dict]) -> dict:
    """Count completed and remaining tasks. An empty plan is not complete."""
    total = len(tasks)
    completed = sum(1 for task in tasks if task.get("completed"))
    remaining = total - completed
    percent = 0 if total == 0 else (100 * completed + total // 2) // total
    return {
        "completed": completed,
        "total": total,
        "remaining": remaining,
        "percent": percent,
        "finished": total > 0 and remaining == 0,
    }


def next_open_task(tasks: list[dict]) -> dict | None:
    """Return the first unfinished task in list order."""
    ordered = sorted(tasks, key=lambda task: (task.get("position", 0), task.get("id", 0)))
    for task in ordered:
        if not task.get("completed"):
            return {"id": task["id"], "label": task["label"]}
    return None


def plan_public(plan) -> dict:
    """Shape one plan for the API. Tasks stay in their saved order."""
    tasks = [
        {
            "id": task.id,
            "label": task.label,
            "completed": bool(task.completed),
            "is_custom": bool(task.is_custom),
            "position": task.position,
        }
        for task in sorted(plan.tasks, key=lambda item: (item.position, item.id))
    ]
    return {
        "id": plan.id,
        "candidate_id": plan.candidate_id,
        "job_id": plan.job_id,
        "notes": plan.notes or "",
        "next_action": plan.next_action or "",
        "tasks": tasks,
        "progress": progress_summary(tasks),
        "next_task": next_open_task(tasks),
    }


def _fail(status: int, message: str) -> PrepResult:
    return PrepResult(False, status, message, None)


def _ok(plan) -> PrepResult:
    return PrepResult(True, 200, "", plan_public(plan))


def ensure_plan(repo, candidate_id: int, job_id: int, title: str, skills: list[str] | None) -> PrepResult:
    """Return this candidate's plan for this job, creating the starter list once."""
    existing = repo.get_plan(candidate_id, job_id)
    if existing is not None:
        return _ok(existing)
    created = repo.create_plan(candidate_id, job_id, starter_labels(title, skills))
    return _ok(created)


def add_task(repo, candidate_id: int, job_id: int, label: str) -> PrepResult:
    """Add a task this candidate wrote. A blank label is refused."""
    cleaned = " ".join(str(label or "").split())
    if not cleaned:
        return _fail(422, "Enter a task.")
    if len(cleaned) > MAX_LABEL:
        return _fail(422, "A task can be 240 characters at most.")
    plan = repo.get_plan(candidate_id, job_id)
    if plan is None:
        return _fail(404, "Open this job before adding a task.")
    if len(plan.tasks) >= MAX_TASKS:
        return _fail(422, "This plan already has 40 tasks.")
    repo.add_task(plan, cleaned)
    return _ok(repo.get_plan(candidate_id, job_id))


def set_task(repo, candidate_id: int, job_id: int, task_id: int, completed: bool) -> PrepResult:
    """Check or uncheck a task on this candidate's plan for this job."""
    plan = repo.get_plan(candidate_id, job_id)
    if plan is None:
        return _fail(404, "Preparation plan not found.")
    task = next((item for item in plan.tasks if item.id == task_id), None)
    if task is None:
        return _fail(404, "Task not found.")
    repo.set_completed(task, bool(completed))
    return _ok(repo.get_plan(candidate_id, job_id))


def remove_task(repo, candidate_id: int, job_id: int, task_id: int) -> PrepResult:
    """Delete a task the candidate added. Starter tasks stay on the plan."""
    plan = repo.get_plan(candidate_id, job_id)
    if plan is None:
        return _fail(404, "Preparation plan not found.")
    task = next((item for item in plan.tasks if item.id == task_id), None)
    if task is None:
        return _fail(404, "Task not found.")
    if not task.is_custom:
        return _fail(409, "Only tasks you added can be deleted.")
    repo.delete_task(task)
    return _ok(repo.get_plan(candidate_id, job_id))


def save_journal(repo, candidate_id: int, job_id: int, notes: str, next_action: str) -> PrepResult:
    """Store notes and the candidate's own next action for this job."""
    cleaned_notes = str(notes or "").strip()
    cleaned_action = " ".join(str(next_action or "").split())
    if len(cleaned_notes) > MAX_NOTES:
        return _fail(422, "Notes are limited to 4000 characters.")
    if len(cleaned_action) > MAX_ACTION:
        return _fail(422, "The next action can be 240 characters at most.")
    plan = repo.get_plan(candidate_id, job_id)
    if plan is None:
        return _fail(404, "Open this job before saving notes.")
    repo.save_journal(plan, cleaned_notes, cleaned_action)
    return _ok(repo.get_plan(candidate_id, job_id))
