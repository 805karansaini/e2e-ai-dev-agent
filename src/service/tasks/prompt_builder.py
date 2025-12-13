from __future__ import annotations

from pathlib import Path
from textwrap import dedent
from typing import Iterable, Union

from loguru import logger

from src.service.jira import JiraContext

from .models import DbTaskContext, TaskPayload


class PromptBuilder:
    """Compose orchestration prompts with Jira context."""

    def __init__(self, base_dir: Path, attachments_dir: Path) -> None:
        self.base_dir = base_dir
        self.attachments_dir = attachments_dir

    def compose(
        self,
        context: Union[JiraContext, DbTaskContext],
        payload: TaskPayload,
        *,
        include_orchestration_preamble: bool = True,
    ) -> str:
        orchestration = (
            self._load_orchestration_prompt() if include_orchestration_preamble else ""
        )

        if isinstance(context, JiraContext):
            task_context_block = self._render_jira_context(context)
            attachments_note = self._render_attachments_note(context)
        else:
            task_context_block = self._render_db_context(context)
            attachments_note = self._render_db_attachments_note(context)

        lines: list[str] = []
        if include_orchestration_preamble:
            lines.append(orchestration.strip())
            lines.append("")
        lines.append(task_context_block.strip())
        lines.append("")
        lines.append("=== REPOSITORY CONTEXT ===")
        lines.append(f"Repository URL: {payload.repo_url}")
        lines.append(f"Base branch: {payload.base_branch}")
        lines.append(attachments_note.strip())
        return "\n".join(lines).strip()

    def orchestration_preamble(self) -> str:
        """System-level instructions for the orchestrator model."""
        return self._load_orchestration_prompt()

    def _render_jira_context(self, context: JiraContext) -> str:
        task = context.task
        labels = ", ".join(task.labels) if task.labels else "None"
        summary = task.summary or "No summary provided"
        description = task.description or "No description provided."

        subtasks = list(task.subtasks)
        lines: list[str] = []
        lines.append("=== JIRA CONTEXT ===")
        lines.append(f"Main task: {task.key}: {summary}")
        lines.append(f"Labels: {labels}")
        lines.append("Description:")
        lines.extend(self._indent_block(description, prefix="  "))
        lines.append("")
        lines.append("Subtasks:")

        if not subtasks:
            lines.append(
                "- (none) Jira has no subtasks; treat the main task as one work item."
            )
        else:
            for sub in subtasks:
                sub_summary = sub.summary or "No summary"
                lines.append(f"- {sub.key}: {sub_summary}")
                sub_description = (
                    sub.description or "No description provided."
                ).strip()
                lines.append("  Description:")
                lines.extend(self._indent_block(sub_description, prefix="    "))

        return "\n".join(lines).strip()

    def _render_attachments_note(self, context: JiraContext) -> str:
        if not context.attachments:
            return "Attachments: none"

        task_dir = self.attachments_dir / context.task.key
        samples = self._format_attachment_samples(context.attachments, limit=8)
        samples_block = "\n".join(f"- {item}" for item in samples)

        lines: list[str] = []
        lines.append(f"Attachments: {len(context.attachments)} file(s) downloaded.")
        lines.append(f"Attachments base dir: {task_dir}")
        lines.append("Sample files:")
        lines.extend(self._indent_block(samples_block, prefix="  "))
        return "\n".join(lines).strip()

    def _render_db_context(self, context: DbTaskContext) -> str:
        labels = "N/A"
        summary = context.summary or "No summary provided"
        description = context.description or "No description provided."

        subtasks = list(context.subtasks or [])
        lines: list[str] = []
        lines.append("=== TASK CONTEXT (DB) ===")
        lines.append(f"Main task: {context.task_id}: {summary}")
        lines.append(f"Labels: {labels}")
        lines.append("Description:")
        lines.extend(self._indent_block(description, prefix="  "))
        lines.append("")
        lines.append("Subtasks:")

        if not subtasks:
            lines.append(
                "- (none) DB has no subtasks; treat the main task as one work item."
            )
        else:
            for sub in subtasks:
                sub_summary = sub.summary or "No summary"
                lines.append(f"- {sub.key}: {sub_summary}")
                sub_description = (
                    sub.description or "No description provided."
                ).strip()
                lines.append("  Description:")
                lines.extend(self._indent_block(sub_description, prefix="    "))

        return "\n".join(lines).strip()

    def _render_db_attachments_note(self, context: DbTaskContext) -> str:
        attachments = context.attachment_path or []
        if not attachments:
            return "Attachments: none"

        # attachment_path rows are stored as [{"filename": ..., "path": ...}, ...]
        samples: list[str] = []
        for item in attachments[:8]:
            if not isinstance(item, dict):
                continue
            filename = item.get("filename")
            path = item.get("path")
            if filename and path:
                samples.append(f"{filename} ({path})")
            elif path:
                samples.append(str(path))
        if len(attachments) > 8:
            samples.append("... (more omitted)")

        lines: list[str] = []
        lines.append(f"Attachments: {len(attachments)} item(s) recorded in DB.")
        lines.append("Sample files:")
        lines.extend(
            self._indent_block("\n".join(f"- {s}" for s in samples), prefix="  ")
        )
        return "\n".join(lines).strip()

    @staticmethod
    def _format_attachment_samples(paths: Iterable[Path], *, limit: int) -> list[str]:
        items: list[str] = []
        for idx, p in enumerate(paths):
            if idx >= limit:
                break
            items.append(str(p))
        if len(items) == limit:
            items.append("... (more omitted)")
        return items

    @staticmethod
    def _indent_block(text: str, *, prefix: str) -> list[str]:
        text = (text or "").rstrip()
        if not text:
            return [f"{prefix}(empty)"]
        return [
            f"{prefix}{line}" if line else prefix.rstrip() for line in text.splitlines()
        ]

    def _load_orchestration_prompt(self) -> str:
        project_root = Path(__file__).resolve().parents[3]
        workdir_root = self.base_dir

        candidates = [
            project_root / "prompts" / "orchestration_prompt_v1.md",
            workdir_root / "prompts" / "orchestration_prompt_v1.md",
            project_root / "prompts" / "orchestration_prompt.md",
            workdir_root / "prompts" / "orchestration_prompt.md",
            project_root / "ORCHESTRATION_PROMPT.md",
            workdir_root / "ORCHESTRATION_PROMPT.md",
        ]

        for prompt_path in candidates:
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
            "Orchestration prompt not found; using fallback prompt. Checked: {paths}",
            paths=", ".join(str(p) for p in candidates),
        )

        return (
            "You are the Task Orchestrator. Generate an execution plan and prompts for "
            "each subtask (or the full task if none are listed). Work sequentially and "
            "summarize as you proceed."
        )


__all__ = ["PromptBuilder"]
