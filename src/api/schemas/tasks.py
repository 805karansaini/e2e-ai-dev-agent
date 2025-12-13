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


class SubtaskPromptSchema(BaseModel):
    """Prompt details for an individual task/subtask."""

    subtask_key: str | None = Field(
        default=None, description="Identifier for the subtask (if applicable)"
    )
    summary: str | None = Field(default=None, description="Short summary of the work")
    description: str | None = Field(
        default=None, description="Detailed description of the subtask"
    )
    prompt: str = Field(..., description="Prompt text to feed into the CLI")


class TaskPlanResponse(BaseModel):
    """Orchestration output that captures the prompts and plan."""

    task_id: str
    repo_url: str
    base_branch: str
    orchestration_prompt: str
    simple_prompt: str
    subtask_prompts: list[SubtaskPromptSchema] = Field(
        default_factory=list,
        description="Prompts for each subtask to run later",
    )
    message: str = "task plan generated"


class TaskStartResponse(BaseModel):
    """Execution start acknowledgement."""

    task_id: str
    started_subtasks: list[str] = Field(
        default_factory=list, description="Identifiers for the queued/started subtasks"
    )
    message: str = "task execution started"


class TaskAutoResponse(BaseModel):
    """Combined orchestration + execution acknowledgement."""

    task_id: str
    orchestration_prompt: str = Field(
        default="",
        description=(
            "Orchestration prompt (if returned). For /tasks/auto this may be empty "
            "because orchestration runs asynchronously; fetch from the DB endpoints instead."
        ),
    )
    started_subtasks: list[str] = Field(
        default_factory=list, description="Identifiers for the started subtasks"
    )
    message: str = "orchestration and execution queued"
