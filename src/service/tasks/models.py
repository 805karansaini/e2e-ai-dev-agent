from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from src.core.config import settings


class TaskPayload(BaseModel):
    """Incoming payload describing a CLINE task to start."""

    task_id: str = Field(..., min_length=1, description="Unique task identifier")
    repo_url: str = Field(..., min_length=1, description="Git repo URL or path")
    base_branch: str = Field(
        default_factory=lambda: settings.DEFAULT_BASE_BRANCH,
        description="Base branch to use for the task",
    )

    @field_validator("task_id", "repo_url", "base_branch")
    @classmethod
    def _strip_and_validate(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Value cannot be empty")
        return cleaned


class SubtaskPlan(BaseModel):
    """Stored prompt details for a task/subtask."""

    subtask_key: str | None = Field(
        default=None, description="Identifier for the subtask (if any)"
    )
    summary: str | None = Field(default=None, description="Short summary of the work")
    description: str | None = Field(
        default=None, description="Detailed description of the subtask"
    )
    prompt: str = Field(..., description="Prompt text to send to the CLI")


class StoredTaskPlan(BaseModel):
    """Collection of prompts and metadata persisted for a task."""

    task_key: str
    repo_url: str
    base_branch: str
    detailed_description: str | None = None
    subtask_prompts: list[SubtaskPlan] = Field(default_factory=list)


class OrchestrationResult(BaseModel):
    """In-memory orchestration result returned by the runner."""

    task_id: str
    repo_url: str
    base_branch: str
    orchestration_prompt: str
    simple_prompt: str
    subtask_prompts: list[SubtaskPlan] = Field(default_factory=list)


class DbSubtaskContext(BaseModel):
    """Database-backed subtask context used by the orchestrator."""

    key: str = Field(..., min_length=1)
    summary: str | None = None
    description: str | None = None
    prompt: str | None = None


class DbTaskContext(BaseModel):
    """Database-backed task context used by the orchestrator/prompt builder."""

    task_id: str = Field(..., min_length=1)
    summary: str | None = None
    description: str | None = None
    attachment_path: list[dict] | None = None
    subtasks: list[DbSubtaskContext] = Field(default_factory=list)


__all__ = [
    "TaskPayload",
    "SubtaskPlan",
    "StoredTaskPlan",
    "OrchestrationResult",
    "DbTaskContext",
    "DbSubtaskContext",
]
