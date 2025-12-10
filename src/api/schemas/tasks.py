"""Schemas for task-related endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.core.config import settings


class TaskCreateRequest(BaseModel):
    """Request body for POST /tasks."""

    task_id: str = Field(..., min_length=1, description="User-supplied task ID")
    repo_url: str = Field(..., min_length=1, description="Repository URL or path")
    base_branch: str = Field(
        default_factory=lambda: settings.DEFAULT_BASE_BRANCH,
        description="Base branch to start from",
    )


class TaskAccepted(BaseModel):
    """Response payload for accepted tasks."""

    task_id: str
    message: str = "task accepted"
