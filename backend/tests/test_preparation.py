"""Preparation plans with an in-memory store. No database connection."""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.preparation import (
    access_error,
    add_task,
    ensure_plan,
    progress_summary,
    remove_task,
    save_journal,
    set_task,
    starter_labels,
)


class MemoryPrep:
    """Stand-in for preparation storage. Plans are separated by candidate and job."""

    def __init__(self):
        self.plans = []
        self.next_plan = 1
        self.next_task = 1

    def get_plan(self, candidate_id, job_id):
        return next(
            (
                plan
                for plan in self.plans
                if plan.candidate_id == candidate_id and plan.job_id == job_id
            ),
            None,
        )

    def create_plan(self, candidate_id, job_id, labels):
        tasks = []
        for position, label in enumerate(labels):
            tasks.append(
                SimpleNamespace(
                    id=self.next_task,
                    label=label,
                    completed=False,
                    is_custom=False,
                    position=position,
                )
            )
            self.next_task += 1
        plan = SimpleNamespace(
            id=self.next_plan,
            candidate_id=candidate_id,
            job_id=job_id,
            notes="",
            next_action="",
            tasks=tasks,
        )
        self.next_plan += 1
        self.plans.append(plan)
        return plan

    def add_task(self, plan, label):
        position = max((task.position for task in plan.tasks), default=-1) + 1
        plan.tasks.append(
            SimpleNamespace(
                id=self.next_task,
                label=label,
                completed=False,
                is_custom=True,
                position=position,
            )
        )
        self.next_task += 1

    def set_completed(self, task, completed):
        task.completed = completed

    def delete_task(self, task):
        for plan in self.plans:
            plan.tasks = [item for item in plan.tasks if item.id != task.id]

    def save_journal(self, plan, notes, next_action):
        plan.notes = notes
        plan.next_action = next_action


def test_starter_tasks_use_the_job_title_and_skills():
    labels = starter_labels("Data Analyst", ["SQL", " Excel ", "", "Python", "Tableau", "Statistics"])
    assert labels[0] == "Read the complete job description for Data Analyst."
    assert "SQL, Excel, Python, Tableau, and 1 more" in labels[1]
    assert "Data Analyst" in labels[4]
    assert all("selection process" not in label.casefold() for label in labels)
    assert len(labels) == 7


def test_progress_counts_and_percent():
    assert progress_summary([]) == {
        "completed": 0,
        "total": 0,
        "remaining": 0,
        "percent": 0,
        "finished": False,
    }
    half = progress_summary([{"completed": True}, {"completed": False}])
    assert half["percent"] == 50
    assert half["remaining"] == 1
    assert half["finished"] is False
    one_of_seven = [{"completed": index == 0} for index in range(7)]
    assert progress_summary(one_of_seven)["percent"] == 14
    done = progress_summary([{"completed": True}, {"completed": True}])
    assert done["percent"] == 100
    assert done["finished"] is True


def test_plans_stay_separate_for_candidates_and_jobs():
    repo = MemoryPrep()
    first = ensure_plan(repo, 1, 7, "Data Analyst", ["SQL"])
    again = ensure_plan(repo, 1, 7, "Data Analyst", ["SQL"])
    other_job = ensure_plan(repo, 1, 8, "Backend Engineer", ["Python"])
    other_person = ensure_plan(repo, 2, 7, "Data Analyst", ["SQL"])
    assert first.plan["id"] == again.plan["id"]
    assert len(again.plan["tasks"]) == 7
    assert other_job.plan["job_id"] == 8
    assert other_job.plan["tasks"][0]["label"] != first.plan["tasks"][0]["label"]
    assert other_person.plan["candidate_id"] == 2
    assert other_person.plan["id"] != first.plan["id"]

    added = add_task(repo, 1, 7, " Practice a SQL case study ")
    assert added.ok
    assert added.plan["tasks"][-1]["is_custom"] is True
    assert len(repo.get_plan(2, 7).tasks) == 7
    custom_id = added.plan["tasks"][-1]["id"]
    starter_id = added.plan["tasks"][0]["id"]

    checked = set_task(repo, 1, 7, custom_id, True)
    assert checked.plan["progress"]["completed"] == 1
    cleared = set_task(repo, 1, 7, custom_id, False)
    assert cleared.plan["progress"]["completed"] == 0
    blocked = set_task(repo, 2, 7, custom_id, True)
    assert blocked.status == 404
    assert repo.get_plan(1, 7).tasks[-1].completed is False

    kept = remove_task(repo, 1, 7, starter_id)
    assert kept.status == 409
    assert kept.message == "Only tasks you added can be deleted."
    removed = remove_task(repo, 1, 7, custom_id)
    assert removed.ok
    assert all(task["id"] != custom_id for task in removed.plan["tasks"])
    assert len(repo.get_plan(2, 7).tasks) == 7

    blank = add_task(repo, 1, 7, "   ")
    assert blank.status == 422
    saved = save_journal(repo, 1, 7, "  Review SQL examples.  ", " Rewrite the summary. ")
    assert saved.plan["notes"] == "Review SQL examples."
    assert saved.plan["next_action"] == "Rewrite the summary."
    assert repo.get_plan(2, 7).notes == ""
    assert repo.get_plan(1, 8).notes == ""
    reopened = ensure_plan(repo, 1, 7, "Data Analyst", ["SQL"])
    assert reopened.plan["notes"] == "Review SQL examples."


def test_another_candidate_is_refused_before_a_plan_is_opened():
    assert access_error(1, 2) == "You cannot open another candidate's profile."
    assert access_error(1, 1) is None


def test_preparation_routes_require_the_signed_in_candidate():
    from routes.preparation import router

    paths = {route.path for route in router.routes}
    assert "/candidates/{candidate_id}/jobs/{job_id}/preparation" in paths
    assert "/candidates/{candidate_id}/jobs/{job_id}/preparation/tasks" in paths
    assert "/candidates/{candidate_id}/jobs/{job_id}/preparation/tasks/{task_id}" in paths
    for route in router.routes:
        names = [dependency.call.__name__ for dependency in route.dependant.dependencies]
        assert "get_current_candidate" in names
