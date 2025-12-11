"""Async task runner that shells out to the CLINE CLI."""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
from asyncio.subprocess import PIPE, create_subprocess_exec
from pathlib import Path
from textwrap import dedent
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from src.core.config import settings
from src.service.database_handler import SQLiteTaskStore
from src.service.jira import (
    JiraClient,
    JiraConfig,
    JiraContext,
    JiraSubtask,
    JiraTask,
    SubtaskPrompt,
)

logger = logging.getLogger(__name__)


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


class TaskRunner:
    """Minimal async runner that serializes CLINE CLI invocations."""

    def __init__(
        self,
        cli_bin: str,
        extra_args: Optional[list[str]] = None,
        workdir: Optional[str] = None,
        db_path: Optional[str] = None,
    ) -> None:
        self.cli_bin = cli_bin
        self.extra_args = extra_args or []
        self.workdir = workdir
        self._base_dir = Path(workdir or os.getcwd())
        self._attachments_dir = self._base_dir / "data" / "jira_attachments"
        self._db_path = (
            Path(db_path) if db_path else self._base_dir / "data" / "tasks.db"
        )
        self._store = SQLiteTaskStore(self._db_path, self._attachments_dir)
        self._queue: asyncio.Queue[TaskPayload] | None = None
        self._worker: asyncio.Task[None] | None = None
        self._started = False

    @property
    def cli_available(self) -> bool:
        """Return True if the CLINE CLI binary is discoverable."""

        return shutil.which(self.cli_bin) is not None

    @property
    def is_running(self) -> bool:
        """Return True if the worker loop is active."""

        return self._started and self._worker is not None and not self._worker.done()

    @property
    def queued_tasks(self) -> int:
        """Return the number of tasks waiting to be processed."""

        return self._queue.qsize() if self._queue else 0

    async def start(self) -> None:
        """Start the background worker."""

        if self._started:
            return

        self._queue = asyncio.Queue()
        self._started = True
        self._worker = asyncio.create_task(self._worker_loop(), name="task-runner")
        logger.info("Task runner started with CLI bin '%s'.", self.cli_bin)

    async def stop(self) -> None:
        """Stop the background worker gracefully."""

        if not self._started:
            return

        self._started = False
        queue = self._queue
        if self._worker:
            self._worker.cancel()
            try:
                await self._worker
            except asyncio.CancelledError:
                logger.debug("Task runner worker cancelled.")

        # Drain queue to unblock shutdown
        while queue and not queue.empty():
            try:
                queue.get_nowait()
                queue.task_done()
            except asyncio.QueueEmpty:
                break

        logger.info("Task runner stopped.")
        self._queue = None
        self._worker = None

    async def enqueue(self, payload: TaskPayload) -> None:
        """Queue a new task for execution."""

        if not self._started or self._queue is None:
            raise RuntimeError("Task runner is not started.")

        await self._queue.put(payload)
        logger.info(
            "Enqueued task '%s' for repo '%s' (branch=%s).",
            payload.task_id,
            payload.repo_url,
            payload.base_branch,
        )

    async def _worker_loop(self) -> None:
        """Continuously process queued tasks."""

        queue = self._queue
        if queue is None:
            return

        while self._started:
            try:
                payload = await queue.get()
            except asyncio.CancelledError:
                break

            try:
                await self._run_task(payload)
            except asyncio.CancelledError:
                break
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "Failed to execute CLINE task '%s': %s", payload.task_id, exc
                )
            finally:
                queue.task_done()

    async def _run_task(self, payload: TaskPayload) -> None:
        """Execute the CLINE CLI for a single task."""

        jira_context = await self._prepare_jira_context(payload)
        await self._persist_context(jira_context, payload)
        prompt = self._compose_orchestration_prompt(jira_context, payload)
        await self._execute_cline(prompt, payload)

    async def _prepare_jira_context(self, payload: TaskPayload) -> JiraContext:
        """Fetch Jira task data, download attachments, and craft prompts."""

        self._ensure_jira_configured()
        self._attachments_dir.mkdir(parents=True, exist_ok=True)

        config = JiraConfig.from_env()
        async with JiraClient(config) as client:
            task = await client.fetch_issue_with_subtasks(payload.task_id)
            if task is None:
                raise RuntimeError(f"Jira task '{payload.task_id}' was not found.")

            attachments = await client.download_attachments_for_task(
                task, self._attachments_dir
            )

        detailed_description = self._render_task_description(task, attachments)
        subtask_prompts = self._build_subtask_prompts(task)

        logger.info(
            "Prepared Jira context for task '%s' with %d subtasks and %d attachments.",
            task.key,
            len(subtask_prompts),
            len(attachments),
        )

        return JiraContext(
            task=task,
            detailed_description=detailed_description,
            subtask_prompts=subtask_prompts,
            attachments=attachments,
        )

    def _ensure_jira_configured(self) -> None:
        """Validate required Jira configuration."""

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

    def _render_task_description(self, task: JiraTask, attachments: list[Path]) -> str:
        """Build a detailed text description for storage and prompting."""

        status = task.status.name if task.status else "Unknown"
        priority = task.priority.name if task.priority else "Unspecified"
        assignee = task.assignee.display_name if task.assignee else "Unassigned"
        reporter = task.reporter.display_name if task.reporter else "Unknown"
        attachment_note = (
            f"{len(attachments)} attachment(s) saved under {self._attachments_dir}"
            if attachments
            else "No attachments downloaded."
        )
        labels = ", ".join(task.labels) if task.labels else "None"

        return dedent(
            f"""
            Jira task {task.key}: {task.summary or 'No summary provided'}
            Status: {status} | Priority: {priority}
            Assignee: {assignee} | Reporter: {reporter}
            Labels: {labels}
            Description:
            {task.description or 'No description provided.'}

            Attachments: {attachment_note}
            """
        ).strip()

    def _build_subtask_prompts(self, task: JiraTask) -> list[SubtaskPrompt]:
        """Create structured prompts for each subtask."""

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
        """Compose a concise but rich prompt for a specific subtask."""

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

            Deliverable:
            Implement this work in the repository. Reference any downloaded Jira
            attachments under {self._attachments_dir / task.key} (subtasks use a
            nested directory named after their key). Keep changes focused on this
            subtask's scope.
            """
        ).strip()

    # --------------------------------------------------------------------- #
    # Persistence
    # --------------------------------------------------------------------- #
    async def _persist_context(
        self, context: JiraContext, payload: TaskPayload
    ) -> None:
        """Store task, subtask, and attachment metadata via the task store."""

        await asyncio.to_thread(
            self._store.persist_context,
            context.task,
            context.subtask_prompts,
            context.attachments,
            context.detailed_description,
            payload.repo_url,
            payload.base_branch,
        )
        logger.info(
            "Persisted task '%s' and %d subtasks to %s.",
            context.task.key,
            len(context.subtask_prompts),
            self._store.db_path,
        )

    # --------------------------------------------------------------------- #
    # CLI orchestration
    # --------------------------------------------------------------------- #
    def _compose_orchestration_prompt(
        self, context: JiraContext, payload: TaskPayload
    ) -> str:
        """Combine orchestration prompt file with Jira context for CLINE."""

        orchestration = self._load_orchestration_prompt()
        subtask_section = (
            "\n\n".join(
                f"- {sub.key}: {sub.summary or 'No summary'}\n{sub.prompt}"
                for sub in context.subtask_prompts
            )
            or "No subtasks identified; treat the parent task as a single work item."
        )

        attachments_note = (
            f"Attachments downloaded under {self._attachments_dir} matching Jira keys."
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
        """Read the orchestration instructions from disk, with a fallback."""

        prompt_path = self._base_dir / "ORCHESTRATION_PROMPT.md"
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

    async def _execute_cline(self, prompt: str, payload: TaskPayload) -> None:
        """Invoke the CLINE CLI with a prepared prompt."""

        if not self.cli_available:
            raise RuntimeError(
                f"CLINE CLI binary '{self.cli_bin}' not found in PATH; cannot start task."
            )

        env = os.environ.copy()
        env.update(
            {
                "TASK_ID": payload.task_id,
                "TASK_REPO_URL": payload.repo_url,
                "TASK_BASE_BRANCH": payload.base_branch,
            }
        )

        command = [
            self.cli_bin,
            "task",
            "new",
            "-y",  # headless/YOLO mode
            *self.extra_args,
            prompt,
        ]

        logger.info("Launching CLINE CLI (headless): %s", " ".join(command))

        try:
            process = await create_subprocess_exec(
                *command, stdout=PIPE, stderr=PIPE, cwd=self.workdir, env=env
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"CLINE CLI binary '{self.cli_bin}' not found in PATH"
            ) from exc

        stdout, stderr = await process.communicate()

        if stdout:
            logger.debug(
                "CLINE CLI stdout for %s: %s", payload.task_id, stdout.decode()
            )
        if stderr:
            logger.debug(
                "CLINE CLI stderr for %s: %s", payload.task_id, stderr.decode()
            )

        if process.returncode != 0:
            raise RuntimeError(
                f"CLINE CLI exited with status {process.returncode} "
                f"for task '{payload.task_id}'"
            )

        logger.info("CLINE task '%s' completed successfully.", payload.task_id)


# Shared task runner instance configured from settings
task_runner = TaskRunner(
    cli_bin=settings.CLINE_CLI_BIN,
    extra_args=settings.CLINE_CLI_ARGS,
    workdir=settings.TASK_WORKDIR,
)
