from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

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


class OrchestratedPromptItem(BaseModel):
    """A prompt generated for insertion into the tasks table."""

    task_id: str = Field(..., min_length=1, description="Parent task identifier")
    task_type: Literal["TASK", "SUBTASK"] = Field(
        ..., description="Whether this prompt is for the parent or a subtask"
    )
    sub_task_id: str | None = Field(
        default=None, description="Subtask identifier (required for SUBTASK prompts)"
    )
    prompt: str = Field(..., min_length=1, description="Prompt to persist into DB")
    agent_summary: str | None = Field(
        default=None, description="Optional short summary for UI/debug"
    )

    @model_validator(mode="after")
    def _validate_type_fields(self) -> "OrchestratedPromptItem":
        if self.task_type == "TASK":
            if self.sub_task_id not in (None, ""):
                raise ValueError("TASK prompt must have sub_task_id = null")
        else:
            if not self.sub_task_id:
                raise ValueError("SUBTASK prompt must include sub_task_id")
        return self


class OrchestratedPromptOutput(BaseModel):
    """Structured OpenRouter output: N prompts (task + subtasks)."""

    prompts: list[OrchestratedPromptItem] = Field(
        ..., description="One prompt per task/subtask row to persist"
    )


__all__ = [
    "TaskPayload",
    "SubtaskPlan",
    "StoredTaskPlan",
    "OrchestrationResult",
    "DbTaskContext",
    "DbSubtaskContext",
    "OrchestratedPromptItem",
    "OrchestratedPromptOutput",
]
