"""Pydantic schemas for database Task CRUD operations."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.service.database_handler.models.task import TaskStatus, TaskType

# String constants for validation
TASK_TYPE_VALUES = [e.value for e in TaskType]
STATUS_VALUES = [e.value for e in TaskStatus]


class AttachmentPath(BaseModel):
    """Schema for attachment path."""

    filename: str = Field(..., description="Attachment filename")
    path: str = Field(..., description="Attachment path")


class TaskBase(BaseModel):
    """Base schema for Task with common fields."""

    task_id: str = Field(
        ..., min_length=1, max_length=128, description="Unique task identifier"
    )
    sub_task_id: Optional[str] = Field(
        None, max_length=128, description="Sub-task identifier"
    )
    task_type: str = Field(default=TaskType.TASK.value, description="Type of task")
    description: Optional[str] = Field(None, description="Task description")
    summary: Optional[str] = Field(None, description="Task summary")
    repo_url: Optional[str] = Field(None, max_length=1024, description="Repository URL")
    base_branch: Optional[str] = Field(None, max_length=256, description="Base branch")
    attachment_path: Optional[List[AttachmentPath]] = Field(
        None, description="Attachment paths"
    )
    status: str = Field(default=TaskStatus.PENDING.value, description="Task status")
    prompt: Optional[str] = Field(None, description="Task prompt")
    agent_summary: Optional[str] = Field(None, description="Agent summary")
    additional_json: Optional[Dict[str, Any]] = Field(
        None, description="Additional JSON data"
    )

    @field_validator("task_type")
    @classmethod
    def validate_task_type(cls, value: str) -> str:
        if value not in TASK_TYPE_VALUES:
            raise ValueError(f"task_type must be one of {TASK_TYPE_VALUES}")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in STATUS_VALUES:
            raise ValueError(f"status must be one of {STATUS_VALUES}")
        return value


class CreateTask(BaseModel):
    """Schema for creating a new task."""

    task_id: str = Field(
        ..., min_length=1, max_length=128, description="Unique task identifier"
    )
    description: Optional[str] = Field(None, description="Task description")
    summary: Optional[str] = Field(None, description="Task summary")
    repo_url: Optional[str] = Field(None, max_length=1024, description="Repository URL")
    base_branch: Optional[str] = Field(None, max_length=256, description="Base branch")
    attachment_path: Optional[List[AttachmentPath]] = Field(
        None, description="Attachment paths"
    )
    status: str = Field(default=TaskStatus.PENDING.value, description="Task status")
    prompt: Optional[str] = Field(None, description="Task prompt")
    agent_summary: Optional[str] = Field(None, description="Agent summary")
    additional_json: Optional[Dict[str, Any]] = Field(
        None, description="Additional JSON data"
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in STATUS_VALUES:
            raise ValueError(f"status must be one of {STATUS_VALUES}")
        return value


class CreateSubTask(BaseModel):
    task_id: str = Field(
        ..., min_length=1, max_length=128, description="Unique task identifier"
    )
    sub_task_id: str = Field(..., max_length=128, description="Sub-task identifier")
    description: Optional[str] = Field(None, description="Task description")
    summary: Optional[str] = Field(None, description="Task summary")
    repo_url: Optional[str] = Field(None, max_length=1024, description="Repository URL")
    base_branch: Optional[str] = Field(None, max_length=256, description="Base branch")
    attachment_path: Optional[List[AttachmentPath]] = Field(
        None, description="Attachment paths"
    )
    status: str = Field(default=TaskStatus.PENDING.value, description="Task status")
    prompt: Optional[str] = Field(None, description="Task prompt")
    agent_summary: Optional[str] = Field(None, description="Agent summary")
    additional_json: Optional[Dict[str, Any]] = Field(
        None, description="Additional JSON data"
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in STATUS_VALUES:
            raise ValueError(f"status must be one of {STATUS_VALUES}")
        return value


class TaskUpdate(BaseModel):
    """Schema for updating an existing task."""

    model_config = ConfigDict(from_attributes=True)

    # All fields are optional for updates
    sub_task_id: Optional[str] = Field(
        None, max_length=128, description="Sub-task identifier"
    )
    task_type: Optional[str] = Field(None, description="Type of task")
    description: Optional[str] = Field(None, description="Task description")
    repo_url: Optional[str] = Field(None, max_length=1024, description="Repository URL")
    base_branch: Optional[str] = Field(None, max_length=256, description="Base branch")
    attachment_path: Optional[List[AttachmentPath]] = Field(
        None, description="Attachment paths"
    )
    status: Optional[str] = Field(None, description="Task status")
    prompt: Optional[str] = Field(None, description="Task prompt")
    summary: Optional[str] = Field(None, description="Task summary")
    agent_summary: Optional[str] = Field(None, description="Agent summary")
    additional_json: Optional[Dict[str, Any]] = Field(
        None, description="Additional JSON data"
    )

    @field_validator("task_type")
    @classmethod
    def validate_task_type(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in TASK_TYPE_VALUES:
            raise ValueError(f"task_type must be one of {TASK_TYPE_VALUES}")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in STATUS_VALUES:
            raise ValueError(f"status must be one of {STATUS_VALUES}")
        return value


class SubTaskUpdate(BaseModel):
    """Schema for updating an existing task."""

    model_config = ConfigDict(from_attributes=True)

    description: Optional[str] = Field(None, description="Task description")
    task_type: Optional[str] = Field(None, description="Type of task")
    repo_url: Optional[str] = Field(None, max_length=1024, description="Repository URL")
    base_branch: Optional[str] = Field(None, max_length=256, description="Base branch")
    attachment_path: Optional[List[AttachmentPath]] = Field(
        None, description="Attachment paths"
    )
    status: Optional[str] = Field(None, description="Task status")
    prompt: Optional[str] = Field(None, description="Task prompt")
    summary: Optional[str] = Field(None, description="Task summary")
    agent_summary: Optional[str] = Field(None, description="Agent summary")
    additional_json: Optional[Dict[str, Any]] = Field(
        None, description="Additional JSON data"
    )

    @field_validator("task_type")
    @classmethod
    def validate_task_type(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in TASK_TYPE_VALUES:
            raise ValueError(f"task_type must be one of {TASK_TYPE_VALUES}")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in STATUS_VALUES:
            raise ValueError(f"status must be one of {STATUS_VALUES}")
        return value


class TaskResponse(TaskBase):
    """Schema for Task response."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Primary key ID")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def serialize_datetime(cls, value):
        """Convert datetime to ISO string."""
        if isinstance(value, datetime):
            return value.isoformat()
        return value


class TaskList(BaseModel):
    """Schema for listing tasks with pagination info."""

    tasks: list[TaskResponse] = Field(..., description="List of tasks")
    total: int = Field(..., description="Total number of tasks")
    skip: int = Field(..., description="Number of tasks skipped")
    limit: Optional[int] = Field(None, description="Maximum number of tasks returned")


class TaskSearchRequest(BaseModel):
    """Schema for task search request."""

    query: Optional[str] = Field(
        None, description="Search query for description, summary, or prompt"
    )
    status: Optional[TaskStatus] = Field(None, description="Filter by task status")
    task_type: Optional[TaskType] = Field(None, description="Filter by task type")
    skip: int = Field(default=0, ge=0, description="Number of tasks to skip")
    limit: Optional[int] = Field(
        None, gt=0, le=1000, description="Maximum number of tasks to return"
    )


class ImportJiraTaskRequest(BaseModel):
    """Schema for importing a task from Jira."""

    jira_task_id: str = Field(
        ..., min_length=1, description="Jira task ID (e.g., PROJ-123)"
    )
    repo_url: str = Field(..., min_length=1, description="Repository URL")
    branch: str = Field(..., min_length=1, description="Branch name")
