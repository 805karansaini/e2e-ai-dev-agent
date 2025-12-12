from __future__ import annotations

from pathlib import Path
from textwrap import dedent
from typing import List, Optional

from src.core.config import settings
from src.service.jira import (
    JiraClient,
    JiraConfig,
    JiraContext,
    JiraSubtask,
    JiraTask,
    SubtaskPrompt,
)

from .models import TaskPayload


class JiraContextBuilder:
    """Build Jira context, subtasks, and attachment metadata."""

    def __init__(self, attachments_dir: Path) -> None:
        self.attachments_dir = attachments_dir

    async def build(self, payload: TaskPayload) -> JiraContext:
        self._ensure_jira_configured()
        self.attachments_dir.mkdir(parents=True, exist_ok=True)

        config = JiraConfig.from_env()
        async with JiraClient(config) as client:
            task = await client.fetch_issue_with_subtasks(payload.task_id)
            if task is None:
                raise RuntimeError(f"Jira task '{payload.task_id}' was not found.")

            attachments = await client.download_attachments_for_task(
                task, self.attachments_dir
            )

        detailed_description = self._render_task_description(task, attachments)
        subtask_prompts = self._build_subtask_prompts(task)

        return JiraContext(
            task=task,
            detailed_description=detailed_description,
            subtask_prompts=subtask_prompts,
            attachments=attachments,
        )

    def _ensure_jira_configured(self) -> None:
        missing = [
            name
            for name in (
                "JIRA_BASE_URL",
                "JIRA_EMAIL",
                "JIRA_API_TOKEN",
                "JIRA_PROJECT_KEY",
            )
            if not getattr(settings, name)
        ]
        if missing:
            raise RuntimeError(
                f"Jira settings missing: {', '.join(missing)}. "
                "Set them to enable Jira-backed task execution."
            )

    def _render_task_description(self, task: JiraTask, attachments: List[Path]) -> str:
        status = task.status.name if task.status else "Unknown"
        priority = task.priority.name if task.priority else "Unspecified"
        assignee = task.assignee.display_name if task.assignee else "Unassigned"
        reporter = task.reporter.display_name if task.reporter else "Unknown"
        attachment_note = (
            f"{len(attachments)} attachment(s) saved under {self.attachments_dir}"
            if attachments
            else "No attachments downloaded."
        )
        labels = ", ".join(task.labels) if task.labels else "None"

        return dedent(
            f"""
            Jira task {task.key}: {task.summary or 'No summary provided'}
            Description:
            {task.description or 'No description provided.'}

            Attachments: {attachment_note}
            """
        ).strip()

    def _build_subtask_prompts(self, task: JiraTask) -> list[SubtaskPrompt]:
        if not task.subtasks:
            prompt = self._compose_subtask_prompt(task, None)
            return [
                SubtaskPrompt(
                    key=task.key,
                    summary=task.summary,
                    description=task.description,
                    prompt=prompt,
                )
            ]

        prompts: list[SubtaskPrompt] = []
        for subtask in task.subtasks:
            prompt = self._compose_subtask_prompt(task, subtask)
            prompts.append(
                SubtaskPrompt(
                    key=subtask.key,
                    summary=subtask.summary,
                    description=subtask.description,
                    prompt=prompt,
                )
            )
        return prompts

    def _compose_subtask_prompt(
        self, task: JiraTask, subtask: Optional[JiraSubtask]
    ) -> str:
        header = (
            f"Subtask {subtask.key}: {subtask.summary or 'No summary'}"
            if subtask
            else f"Task {task.key}: {task.summary or 'No summary'}"
        )
        subtask_description = (
            subtask.description if subtask else task.description
        ) or "No description provided."
        parent_description = task.description or "No description provided."

        return dedent(
            f"""
            Parent task {task.key}: {task.summary or 'No summary provided'}
            Parent description:
            {parent_description}

            {header}
            Details:
            {subtask_description}
            """
        ).strip()


__all__ = ["JiraContextBuilder"]
