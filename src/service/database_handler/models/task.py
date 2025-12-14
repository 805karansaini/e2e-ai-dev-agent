from __future__ import annotations

import enum

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Enum,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)

from .base import Base


class TaskStatus(enum.Enum):
    PENDING = "PENDING"
    PLANNING = "PLANNING"
    READY = "READY"
    QUEUED = "QUEUED"
    IN_PROGRESS = "IN_PROGRESS"
    REVIEWING = "REVIEWING"
    PULL_REQUEST = "PULL_REQUEST"
    DONE = "DONE"
    FAILURE = "FAILURE"


class TaskType(enum.Enum):
    TASK = "TASK"
    SUBTASK = "SUBTASK"


class Task(Base):
    """Represents a top-level task."""

    __tablename__ = "tasks"
    __table_args__ = (
        # Prevent duplicate *parent* task rows when sub_task_id is NULL.
        # SQLite UNIQUE constraints allow multiple NULLs, so we use a partial index.
        Index(
            "uq_tasks_parent_task_id",
            "task_id",
            unique=True,
            sqlite_where=text("sub_task_id IS NULL AND task_type = 'TASK'"),
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(128), index=True)
    sub_task_id = Column(String(128), unique=True, index=True, nullable=True)
    task_type = Column(Enum(TaskType), nullable=False, default=TaskType.TASK)
    repo_url = Column(String(1024), nullable=True)
    base_branch = Column(String(256), nullable=True)
    status = Column(Enum(TaskStatus), nullable=False, default=TaskStatus.PENDING)

    # Jira's Title/Summary, Description, Attachments
    summary = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    attachment_path = Column(JSON, nullable=True)

    # Agent's Prompt, Agent's Summary, Additional JSON
    prompt = Column(Text, nullable=True)
    agent_summary = Column(Text, nullable=True)

    additional_json = Column(JSON, nullable=True)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
