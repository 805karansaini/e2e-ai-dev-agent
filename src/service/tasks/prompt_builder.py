from __future__ import annotations

import logging
from pathlib import Path
from textwrap import dedent

from src.service.jira import JiraContext

from .models import TaskPayload

logger = logging.getLogger(__name__)


class PromptBuilder:
    """Compose orchestration prompts with Jira context."""

    def __init__(self, base_dir: Path, attachments_dir: Path) -> None:
        self.base_dir = base_dir
        self.attachments_dir = attachments_dir

    def compose(self, context: JiraContext, payload: TaskPayload) -> str:
        orchestration = self._load_orchestration_prompt()
        subtask_section = (
            "\n\n".join(
                f"- {sub.key}: {sub.summary or 'No summary'}\n{sub.prompt}"
                for sub in context.subtask_prompts
            )
            or "No subtasks identified; treat the parent task as a single work item."
        )

        attachments_note = (
            f"Attachments downloaded under {self.attachments_dir} matching Jira keys."
            if context.attachments
            else "No attachments were available in Jira."
        )

        return dedent(
            f"""
            {orchestration}

            === Jira Context ===
            {context.detailed_description}

            Subtask prompts:
            {subtask_section}

            Repository: {payload.repo_url}
            Base branch: {payload.base_branch}
            {attachments_note}
            """
        ).strip()

    def _load_orchestration_prompt(self) -> str:
        prompt_path = self.base_dir / "ORCHESTRATION_PROMPT.md"
        if prompt_path.exists():
            try:
                return prompt_path.read_text(encoding="utf-8").strip()
            except OSError as exc:
                logger.warning("Failed to read orchestration prompt: %s", exc)
        else:
            logger.warning(
                "ORCHESTRATION_PROMPT.md not found at %s; using fallback prompt.",
                prompt_path,
            )

        return (
            "Coordinate CLINE tasks by enumerating subtasks, executing them one by one, "
            "and tracking progress until the parent task is complete."
        )


__all__ = ["PromptBuilder"]
