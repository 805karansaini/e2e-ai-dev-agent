"""Pydantic schemas for database Task CRUD operations."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, ConfigDict

from src.service.database_handler.models.task import TaskStatus, TaskType

class AttachmentPath(BaseModel):
    """Schema for attachment path."""
    filename: str = Field(..., description="Attachment filename")
    path: str = Field(..., description="Attachment path")


class TaskBase(BaseModel):
    """Base schema for Task with common fields."""

    task_id: str = Field(..., min_length=1, max_length=128, description="Unique task identifier")
    sub_task_id: Optional[str] = Field(None, max_length=128, description="Sub-task identifier")
    task_type: TaskType = Field(default=TaskType.TASK, description="Type of task")
    description: Optional[str] = Field(None, description="Task description")
    repo_url: Optional[str] = Field(None, max_length=1024, description="Repository URL")
    base_branch: Optional[str] = Field(None, max_length=256, description="Base branch")
    attachment_path: Optional[List[AttachmentPath]] = Field(None, description="Attachment paths")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Task status")
    prompt: Optional[str] = Field(None, description="Task prompt")
    summary: Optional[str] = Field(None, description="Task summary")
    additional_json: Optional[Dict[str, Any]] = Field(None, description="Additional JSON data")


class TaskCreate(TaskBase):
    """Schema for creating a new task."""

    model_config = ConfigDict(from_attributes=True)

    # All fields are optional except task_id which is required
    task_id: str = Field(..., min_length=1, max_length=128, description="Unique task identifier")
    sub_task_id: Optional[str] = Field(None, max_length=128, description="Sub-task identifier")
    task_type: TaskType = Field(default=TaskType.TASK, description="Type of task")
    description: Optional[str] = Field(None, description="Task description")
    repo_url: Optional[str] = Field(None, max_length=1024, description="Repository URL")
    base_branch: Optional[str] = Field(None, max_length=256, description="Base branch")
    attachment_path: Optional[List[AttachmentPath]] = Field(None, description="Attachment paths")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Task status")
    prompt: Optional[str] = Field(None, description="Task prompt")
    summary: Optional[str] = Field(None, description="Task summary")
    additional_json: Optional[Dict[str, Any]] = Field(None, description="Additional JSON data")


class TaskUpdate(BaseModel):
    """Schema for updating an existing task."""

    model_config = ConfigDict(from_attributes=True)

    # All fields are optional for updates
    task_id: Optional[str] = Field(None, min_length=1, max_length=128, description="Unique task identifier")
    sub_task_id: Optional[str] = Field(None, max_length=128, description="Sub-task identifier")
    task_type: Optional[TaskType] = Field(None, description="Type of task")
    description: Optional[str] = Field(None, description="Task description")
    repo_url: Optional[str] = Field(None, max_length=1024, description="Repository URL")
    base_branch: Optional[str] = Field(None, max_length=256, description="Base branch")
    attachment_path: Optional[List[AttachmentPath]] = Field(None, description="Attachment paths")
    status: Optional[TaskStatus] = Field(None, description="Task status")
    prompt: Optional[str] = Field(None, description="Task prompt")
    summary: Optional[str] = Field(None, description="Task summary")
    additional_json: Optional[Dict[str, Any]] = Field(None, description="Additional JSON data")


class TaskResponse(TaskBase):
    """Schema for Task response."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Primary key ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class TaskList(BaseModel):
    """Schema for listing tasks with pagination info."""

    tasks: list[TaskResponse] = Field(..., description="List of tasks")
    total: int = Field(..., description="Total number of tasks")
    skip: int = Field(..., description="Number of tasks skipped")
    limit: Optional[int] = Field(None, description="Maximum number of tasks returned")


class TaskSearchRequest(BaseModel):
    """Schema for task search request."""

    query: Optional[str] = Field(None, description="Search query for description, summary, or prompt")
    status: Optional[TaskStatus] = Field(None, description="Filter by task status")
    task_type: Optional[TaskType] = Field(None, description="Filter by task type")
    skip: int = Field(default=0, ge=0, description="Number of tasks to skip")
    limit: Optional[int] = Field(None, gt=0, le=1000, description="Maximum number of tasks to return")
