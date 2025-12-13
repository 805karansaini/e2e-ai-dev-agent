from typing import Any, Dict, List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from .config import get_db_session
from .models.task import Task, TaskStatus, TaskType


class TaskCRUD:
    """CRUD operations for Task model."""

    @staticmethod
    def create_task(
        db: Session,
        task_id: str,
        sub_task_id: Optional[str] = None,
        task_type: str = TaskType.TASK.value,  # Accept string
        description: Optional[str] = None,
        repo_url: Optional[str] = None,
        base_branch: Optional[str] = None,
        attachment_path: Optional[Dict[str, Any]] = None,
        status: str = TaskStatus.PENDING.value,  # Accept string
        prompt: Optional[str] = None,
        summary: Optional[str] = None,
        agent_summary: Optional[str] = None,
        additional_json: Optional[Dict[str, Any]] = None,
    ) -> Task:
        """Create a new task."""
        task = Task(
            task_id=task_id,
            sub_task_id=sub_task_id,
            task_type=TaskType(task_type),  # Convert string to enum
            description=description,
            repo_url=repo_url,
            base_branch=base_branch,
            attachment_path=attachment_path,
            status=TaskStatus(status),  # Convert string to enum
            prompt=prompt,
            summary=summary,
            agent_summary=agent_summary,
            additional_json=additional_json,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def get_task_by_id(db: Session, task_id: int) -> Optional[Task]:
        """Get task by primary key ID."""
        return db.query(Task).filter(Task.id == task_id).first()

    @staticmethod
    def get_sub_task_by_sub_task_id(db: Session, sub_task_id: str) -> Optional[Task]:
        """Get Sub-task by primary key ID."""
        return db.query(Task).filter(Task.sub_task_id == sub_task_id).first()

    @staticmethod
    def get_task_by_task_id(db: Session, task_id: str) -> Optional[Task]:
        """Get a top-level (parent) task by task_id.

        Note: Subtasks share the same task_id, so callers expecting the parent
        must filter on task_type + sub_task_id.
        """
        return (
            db.query(Task)
            .filter(Task.task_id == task_id)
            .filter(Task.task_type == TaskType.TASK)
            .filter(Task.sub_task_id.is_(None))
            .first()
        )

    @staticmethod
    def get_tasks_by_status(db: Session, status: TaskStatus) -> List[Task]:
        """Get all tasks with a specific status."""
        return db.query(Task).filter(Task.status == status).all()

    @staticmethod
    def get_all_tasks(
        db: Session, skip: int = 0, limit: Optional[int] = None
    ) -> List[Task]:
        """Get all tasks with optional pagination."""
        query = db.query(Task).offset(skip)
        if limit:
            query = query.limit(limit)
        return query.all()

    @staticmethod
    def update_task(db: Session, task_id: int, **kwargs) -> Optional[Task]:
        """Update task fields."""
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return None

        for key, value in kwargs.items():
            if hasattr(task, key):
                if value is not None:
                    if key == "status" and isinstance(value, str):
                        value = TaskStatus(value)
                    elif key == "task_type" and isinstance(value, str):
                        value = TaskType(value)
                setattr(task, key, value)

        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def update_task_status(
        db: Session, task_id: int, status: TaskStatus
    ) -> Optional[Task]:
        """Update task status."""
        return TaskCRUD.update_task(db, task_id, status=status)

    @staticmethod
    def delete_task(db: Session, task_id: int) -> bool:
        """Delete a task by ID."""
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return False

        db.delete(task)
        db.commit()
        return True

    @staticmethod
    def search_tasks(
        db: Session,
        query: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        task_type: Optional[TaskType] = None,
        skip: int = 0,
        limit: Optional[int] = None,
    ) -> List[Task]:
        """Search tasks with filters."""
        q = db.query(Task)

        if query:
            # Search in description, summary, and prompt
            search_filter = or_(
                Task.description.ilike(f"%{query}%"),
                Task.summary.ilike(f"%{query}%"),
                Task.prompt.ilike(f"%{query}%"),
            )
            q = q.filter(search_filter)

        if status:
            q = q.filter(Task.status == status)

        if task_type:
            q = q.filter(Task.task_type == task_type)

        q = q.offset(skip)
        if limit:
            q = q.limit(limit)

        return q.all()


# Convenience functions that handle session management
def create_task_with_session(**kwargs) -> Task:
    """Create a task with automatic session management."""
    db = get_db_session()
    try:
        return TaskCRUD.create_task(db, **kwargs)
    finally:
        db.close()


def get_task_with_session(task_id: int) -> Optional[Task]:
    """Get task by ID with automatic session management."""
    db = get_db_session()
    try:
        return TaskCRUD.get_task_by_id(db, task_id)
    finally:
        db.close()
