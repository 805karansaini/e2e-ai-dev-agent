from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from loguru import logger

from src.service.jira import JiraContext

from .models import TaskPayload


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
        project_prompt = Path(__file__).resolve().parents[3] / "ORCHESTRATION_PROMPT.md"
        workdir_prompt = self.base_dir / "ORCHESTRATION_PROMPT.md"

        for prompt_path in (project_prompt, workdir_prompt):
            if not prompt_path.exists():
                continue
            try:
                return prompt_path.read_text(encoding="utf-8").strip()
            except OSError as exc:
                logger.warning(
                    "Failed to read orchestration prompt at {path}: {error}",
                    path=prompt_path,
                    error=exc,
                )

        logger.warning(
            "ORCHESTRATION_PROMPT.md not found at {project} or {workdir}; using fallback prompt.",
            project=project_prompt,
            workdir=workdir_prompt,
        )

        return (
            "Use the Jira description and subtask prompts below to plan work, "
            "execute each subtask sequentially, and summarize progress as you go."
        )


__all__ = ["PromptBuilder"]
