from __future__ import annotations

import asyncio
from pathlib import Path

from sqlalchemy.orm import Session

from src.service.database_handler.config import create_tables, get_db_session
from src.service.database_handler.models.task import Task, TaskType
from src.service.jira import JiraContext

from .models import DbSubtaskContext, DbTaskContext, StoredTaskPlan, TaskPayload


class TaskPersistence:
    """Persist Jira context and prompts to the SQLAlchemy-backed task table."""

    def __init__(self, attachments_dir: Path) -> None:
        self._attachments_dir = Path(attachments_dir)

    async def persist(self, context: JiraContext, payload: TaskPayload) -> None:
        await asyncio.to_thread(self._persist_sync, context, payload)

    async def load_plan(self, task_key: str) -> StoredTaskPlan | None:
        return await asyncio.to_thread(self._load_plan_sync, task_key)

    async def load_task_context(self, task_key: str) -> DbTaskContext | None:
        """Load parent task + all subtasks from the DB (prompts may be empty)."""
        return await asyncio.to_thread(self._load_task_context_sync, task_key)

    async def persist_orchestration_prompts(
        self,
        *,
        task_key: str,
        parent_prompt: str | None,
        subtask_prompts: dict[str, str],
        payload: TaskPayload,
    ) -> None:
        """Persist generated prompts for parent/subtasks into the DB."""
        await asyncio.to_thread(
            self._persist_orchestration_prompts_sync,
            task_key,
            parent_prompt,
            subtask_prompts,
            payload,
        )

    # ---- Internals --------------------------------------------------------------
    def _persist_sync(self, context: JiraContext, payload: TaskPayload) -> None:
        # Ensure schema exists (safe to call repeatedly).
        create_tables()

        db = get_db_session()
        try:
            self._upsert_parent_task(db, context, payload)
            self._upsert_subtasks(db, context, payload)
            db.commit()
        finally:
            db.close()

    def _upsert_parent_task(
        self, db: Session, context: JiraContext, payload: TaskPayload
    ) -> None:
        parent = (
            db.query(Task)
            .filter(Task.task_id == context.task.key)
            .filter(Task.task_type == TaskType.TASK)
            .filter(Task.sub_task_id.is_(None))
            .first()
        )

        attachments_json = [
            {"filename": p.name, "path": str(p)} for p in (context.attachments or [])
        ] or None

        if parent is None:
            parent = Task(
                task_id=context.task.key,
                sub_task_id=None,
                task_type=TaskType.TASK,
            )
            db.add(parent)

        parent.summary = context.task.summary or context.task.key
        # Store the rich, rendered context as the "description" used by CLI execution.
        parent.description = context.detailed_description
        parent.repo_url = payload.repo_url
        parent.base_branch = payload.base_branch
        parent.attachment_path = attachments_json

        # Preserve raw Jira payload for debugging/filtering via additional_json.
        parent.additional_json = {
            "jira_key": context.task.key,
            "jira_summary": context.task.summary,
            "jira_description": context.task.description,
            "jira_labels": context.task.labels or [],
        }

    def _upsert_subtasks(
        self, db: Session, context: JiraContext, payload: TaskPayload
    ) -> None:
        for sub in context.subtask_prompts or []:
            if not sub.key:
                continue
            # Safety: some flows may add a fallback "single work item" prompt with
            # the *parent* Jira key when there are no subtasks. Persisting that as a
            # SUBTASK row duplicates the parent task (TASK) row. Never treat the
            # parent key as a subtask identifier.
            if sub.key == context.task.key:
                continue

            row = (
                db.query(Task)
                .filter(Task.sub_task_id == sub.key)
                .filter(Task.task_type == TaskType.SUBTASK)
                .first()
            )

            if row is None:
                row = Task(
                    task_id=context.task.key,
                    sub_task_id=sub.key,
                    task_type=TaskType.SUBTASK,
                )
                db.add(row)

            row.summary = sub.summary
            row.description = sub.description
            row.prompt = sub.prompt
            row.repo_url = payload.repo_url
            row.base_branch = payload.base_branch

    def _load_plan_sync(self, task_key: str) -> StoredTaskPlan | None:
        create_tables()

        db = get_db_session()
        try:
            parent = (
                db.query(Task)
                .filter(Task.task_id == task_key)
                .filter(Task.task_type == TaskType.TASK)
                .filter(Task.sub_task_id.is_(None))
                .first()
            )
            if parent is None:
                return None

            sub_rows = (
                db.query(Task)
                .filter(Task.task_id == task_key)
                .filter(Task.task_type == TaskType.SUBTASK)
                .order_by(Task.sub_task_id.asc())
                .all()
            )

            from .models import SubtaskPlan

            subtask_prompts = [
                SubtaskPlan(
                    subtask_key=row.sub_task_id,
                    summary=row.summary,
                    description=row.description,
                    prompt=row.prompt or "",
                )
                for row in sub_rows
                if row.prompt
            ]

            # If no subtask prompts exist, allow executing the parent prompt (if present).
            if not subtask_prompts and (parent.prompt or "").strip():
                subtask_prompts = [
                    SubtaskPlan(
                        subtask_key=task_key,
                        summary=parent.summary,
                        description=parent.description,
                        prompt=(parent.prompt or "").strip(),
                    )
                ]

            return StoredTaskPlan(
                task_key=task_key,
                repo_url=parent.repo_url or "",
                base_branch=parent.base_branch or "",
                detailed_description=parent.description,
                subtask_prompts=subtask_prompts,
            )
        finally:
            db.close()

    def _load_task_context_sync(self, task_key: str) -> DbTaskContext | None:
        """Load parent + subtasks regardless of whether prompts exist."""
        create_tables()

        db = get_db_session()
        try:
            parent = (
                db.query(Task)
                .filter(Task.task_id == task_key)
                .filter(Task.task_type == TaskType.TASK)
                .filter(Task.sub_task_id.is_(None))
                .first()
            )
            if parent is None:
                return None

            subtasks = (
                db.query(Task)
                .filter(Task.task_id == task_key)
                .filter(Task.task_type == TaskType.SUBTASK)
                .order_by(Task.sub_task_id.asc())
                .all()
            )

            return DbTaskContext(
                task_id=task_key,
                summary=parent.summary,
                description=parent.description,
                attachment_path=parent.attachment_path,
                subtasks=[
                    DbSubtaskContext(
                        key=row.sub_task_id or "",
                        summary=row.summary,
                        description=row.description,
                        prompt=row.prompt,
                    )
                    for row in subtasks
                    if row.sub_task_id
                ],
            )
        finally:
            db.close()

    def _persist_orchestration_prompts_sync(
        self,
        task_key: str,
        parent_prompt: str | None,
        subtask_prompts: dict[str, str],
        payload: TaskPayload,
    ) -> None:
        create_tables()

        db = get_db_session()
        try:
            parent = (
                db.query(Task)
                .filter(Task.task_id == task_key)
                .filter(Task.task_type == TaskType.TASK)
                .filter(Task.sub_task_id.is_(None))
                .first()
            )
            if parent is None:
                raise RuntimeError(f"Task '{task_key}' not found in DB.")

            # Keep repo fields in sync with orchestration request.
            parent.repo_url = payload.repo_url
            parent.base_branch = payload.base_branch

            if parent_prompt is not None:
                cleaned = parent_prompt.strip()
                parent.prompt = cleaned or None

            # Update all subtask prompts.
            for sub_key, prompt in (subtask_prompts or {}).items():
                if not sub_key:
                    continue
                if sub_key == task_key:
                    # Never treat the parent key as a subtask row.
                    continue

                row = (
                    db.query(Task)
                    .filter(Task.sub_task_id == sub_key)
                    .filter(Task.task_type == TaskType.SUBTASK)
                    .first()
                )
                if row is None:
                    # Best-effort: create missing subtask rows.
                    row = Task(
                        task_id=task_key,
                        sub_task_id=sub_key,
                        task_type=TaskType.SUBTASK,
                    )
                    db.add(row)

                row.repo_url = payload.repo_url
                row.base_branch = payload.base_branch
                cleaned = (prompt or "").strip()
                row.prompt = cleaned or None

            db.commit()
        finally:
            db.close()


__all__ = ["TaskPersistence"]
