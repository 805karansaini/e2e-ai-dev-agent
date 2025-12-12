"""Reusable task service logic shared by API routes and internal callers."""

from __future__ import annotations

from typing import Iterable, Optional, Tuple

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.schemas import CreateSubTask, CreateTask, SubTaskUpdate, TaskUpdate
from src.service.database_handler.crud import TaskCRUD
from src.service.database_handler.models.task import Task, TaskStatus, TaskType


class TaskServiceError(Exception):
    """Base exception for task service failures."""


class TaskNotFoundError(TaskServiceError):
    """Raised when a task or sub-task cannot be found."""


class TaskConflictError(TaskServiceError):
    """Raised when a uniqueness constraint is violated."""


class TaskService:
    """High-level task operations that wrap TaskCRUD for reuse."""

    def __init__(self, db: Session):
        self.db = db

    # ---- Create -----------------------------------------------------------------
    def create_task(self, payload: CreateTask) -> Task:
        return self._create(payload, task_type=TaskType.TASK)

    def create_sub_task(self, payload: CreateSubTask) -> Task:
        return self._create(
            payload, task_type=TaskType.SUBTASK, sub_task_id=payload.sub_task_id
        )

    def _create(
        self,
        payload: CreateTask | CreateSubTask,
        task_type: TaskType,
        sub_task_id: Optional[str] = None,
    ) -> Task:
        try:
            return TaskCRUD.create_task(
                db=self.db,
                task_id=payload.task_id,
                sub_task_id=sub_task_id,
                task_type=task_type.value,
                description=payload.description,
                repo_url=payload.repo_url,
                base_branch=payload.base_branch,
                attachment_path=self._attachment_path(payload.attachment_path),
                status=payload.status,
                prompt=payload.prompt,
                summary=payload.summary,
                agent_summary=payload.agent_summary,
                additional_json=payload.additional_json,
            )
        except IntegrityError as exc:
            raise TaskConflictError(
                "Task with the given task_id or sub_task_id already exists."
            ) from exc
        except Exception as exc:  # pragma: no cover - defensive
            raise TaskServiceError(f"Unable to create task {payload.task_id}") from exc

    # ---- Read -------------------------------------------------------------------
    def get_task(self, task_id: str) -> Task:
        task = TaskCRUD.get_task_by_task_id(self.db, task_id)
        if not task:
            raise TaskNotFoundError(f"Task with task_id '{task_id}' not found.")
        return task

    def get_sub_task(self, sub_task_id: str) -> Task:
        sub_task = TaskCRUD.get_sub_task_by_sub_task_id(self.db, sub_task_id)
        if not sub_task:
            raise TaskNotFoundError(
                f"Sub-task with sub_task_id '{sub_task_id}' not found."
            )
        return sub_task

    def list_tasks(
        self,
        skip: int = 0,
        limit: Optional[int] = None,
        status_filter: Optional[TaskStatus] = None,
        task_type_filter: Optional[TaskType] = None,
        query: Optional[str] = None,
    ) -> Tuple[list[Task], int]:
        """Return tasks and the total count for the given filters."""
        filters_present = any([status_filter, task_type_filter, query])

        if filters_present:
            tasks = TaskCRUD.search_tasks(
                db=self.db,
                query=query,
                status=status_filter,
                task_type=task_type_filter,
                skip=skip,
                limit=limit,
            )
            total = self._count_filtered(status_filter, task_type_filter, query)
        else:
            tasks = TaskCRUD.get_all_tasks(db=self.db, skip=skip, limit=limit)
            total = self.db.query(Task).count()

        return tasks, total

    def _count_filtered(
        self,
        status_filter: Optional[TaskStatus],
        task_type_filter: Optional[TaskType],
        query: Optional[str],
    ) -> int:
        total_query = self.db.query(Task)
        if query:
            from sqlalchemy import or_

            search_filter = or_(
                Task.description.ilike(f"%{query}%"),
                Task.summary.ilike(f"%{query}%"),
                Task.prompt.ilike(f"%{query}%"),
            )
            total_query = total_query.filter(search_filter)
        if status_filter:
            total_query = total_query.filter(Task.status == status_filter)
        if task_type_filter:
            total_query = total_query.filter(Task.task_type == task_type_filter)
        return total_query.count()

    # ---- Update -----------------------------------------------------------------
    def update_task(self, task_id: str, payload: TaskUpdate) -> Task:
        task = self.get_task(task_id)
        return self._update(task.id, payload)

    def update_sub_task(self, sub_task_id: str, payload: SubTaskUpdate) -> Task:
        task = self.get_sub_task(sub_task_id)
        return self._update(task.id, payload)

    def _update(self, db_task_id: int, payload: TaskUpdate | SubTaskUpdate) -> Task:
        update_data = payload.model_dump(exclude_unset=True)

        if (
            "attachment_path" in update_data
            and update_data["attachment_path"] is not None
        ):
            update_data["attachment_path"] = self._attachment_path(
                update_data["attachment_path"]
            )

        try:
            updated = TaskCRUD.update_task(self.db, db_task_id, **update_data)
        except IntegrityError as exc:
            raise TaskConflictError(
                "Task with the given identifiers already exists."
            ) from exc
        except Exception as exc:  # pragma: no cover - defensive
            raise TaskServiceError(f"Unable to update task id '{db_task_id}'.") from exc

        if not updated:
            raise TaskNotFoundError("Task to update no longer exists.")

        return updated

    # ---- Delete -----------------------------------------------------------------
    def delete_task(self, task_id: str) -> None:
        task = self.get_task(task_id)
        self._delete(task.id)

    def delete_sub_task(self, sub_task_id: str) -> None:
        task = self.get_sub_task(sub_task_id)
        self._delete(task.id)

    def _delete(self, db_task_id: int) -> None:
        try:
            deleted = TaskCRUD.delete_task(self.db, db_task_id)
        except Exception as exc:  # pragma: no cover - defensive
            raise TaskServiceError(f"Unable to delete task id '{db_task_id}'.") from exc

        if not deleted:
            raise TaskNotFoundError("Task to delete no longer exists.")

    # ---- Helpers ----------------------------------------------------------------
    @staticmethod
    def _attachment_path(attachments: Optional[Iterable]) -> Optional[list[dict]]:
        """Convert attachment pydantic models to a JSON-serializable list."""
        if not attachments:
            return None
        return [{"filename": ap.filename, "path": ap.path} for ap in attachments]
