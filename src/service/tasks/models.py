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


__all__ = ["TaskPayload"]
