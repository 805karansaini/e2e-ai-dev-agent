from __future__ import annotations

import enum

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Enum,
    Integer,
    String,
    Text,
    func,
)

from .base import Base


class TaskStatus(enum.Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class TaskType(enum.Enum):
    TASK = "TASK"
    SUBTASK = "SUBTASK"


class Task(Base):
    """Represents a top-level task."""

    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(128), unique=True, index=True)
    sub_task_id = Column(String(128), unique=True, index=True)

    task_type = Column(Enum(TaskType), nullable=False, default=TaskType.TASK)

    description = Column(Text, nullable=True)
    repo_url = Column(String(1024), nullable=True)
    base_branch = Column(String(256), nullable=True)

    attachment_path = Column(JSON, nullable=True)

    status = Column(Enum(TaskStatus), nullable=False, default=TaskStatus.PENDING)

    prompt = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)

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
