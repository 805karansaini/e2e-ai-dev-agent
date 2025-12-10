from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel

from .models import JiraTask


class SubtaskPrompt(BaseModel):
    """Prompt details for a specific Jira task or subtask."""

    key: str
    summary: Optional[str] = None
    description: Optional[str] = None
    prompt: str


class JiraContext(BaseModel):
    """Aggregated Jira context used for orchestration and persistence."""

    task: JiraTask
    detailed_description: str
    subtask_prompts: List[SubtaskPrompt]
    attachments: List[Path]


__all__ = ["JiraContext", "SubtaskPrompt"]
