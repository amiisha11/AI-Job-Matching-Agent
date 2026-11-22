"""SQL storage for preparation plans.

The service decides the rules. This module only reads and writes rows for the
candidate and job it is given.
"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from models import PreparationPlan, PreparationTask


class SqlPreparationRepo:
    """Store one plan per candidate and job."""

    def __init__(self, db: Session):
        self.db = db

    def get_plan(self, candidate_id: int, job_id: int) -> PreparationPlan | None:
        return self.db.scalar(
            select(PreparationPlan)
            .where(
                PreparationPlan.candidate_id == candidate_id,
                PreparationPlan.job_id == job_id,
            )
            .options(selectinload(PreparationPlan.tasks))
        )

    def create_plan(self, candidate_id: int, job_id: int, labels: list[str]) -> PreparationPlan:
        plan = PreparationPlan(
            candidate_id=candidate_id,
            job_id=job_id,
            notes="",
            next_action="",
        )
        self.db.add(plan)
        try:
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            existing = self.get_plan(candidate_id, job_id)
            if existing is not None:
                return existing
            raise
        for position, label in enumerate(labels):
            self.db.add(
                PreparationTask(
                    plan_id=plan.id,
                    label=label,
                    completed=False,
                    is_custom=False,
                    position=position,
                )
            )
        self.db.commit()
        stored = self.get_plan(candidate_id, job_id)
        if stored is None:
            raise RuntimeError("The preparation plan was not stored.")
        return stored

    def add_task(self, plan: PreparationPlan, label: str) -> None:
        position = max((task.position for task in plan.tasks), default=-1) + 1
        self.db.add(
            PreparationTask(
                plan_id=plan.id,
                label=label,
                completed=False,
                is_custom=True,
                position=position,
            )
        )
        self.db.commit()

    def set_completed(self, task: PreparationTask, completed: bool) -> None:
        task.completed = completed
        self.db.commit()

    def delete_task(self, task: PreparationTask) -> None:
        self.db.delete(task)
        self.db.commit()

    def save_journal(self, plan: PreparationPlan, notes: str, next_action: str) -> None:
        plan.notes = notes
        plan.next_action = next_action
        self.db.commit()
