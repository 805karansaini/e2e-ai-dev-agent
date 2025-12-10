"""Async task runner that shells out to the CLINE CLI."""

from __future__ import annotations

import asyncio
import logging
import shutil
from asyncio.subprocess import PIPE, create_subprocess_exec
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from src.core.config import settings

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
    ) -> None:
        self.cli_bin = cli_bin
        self.extra_args = extra_args or []
        self.workdir = workdir
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

        prompt = (
            f"[{payload.task_id}] repo: {payload.repo_url}, "
            f"base_branch: {payload.base_branch}"
        )
        prompt = f"Please generate a text file with current date and time as name in YYYY-MM-DD_HH-MM-SS format in the current directory. And please say 'Hi from Cline CLI {payload.task_id}' in the file."
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
                *command, stdout=PIPE, stderr=PIPE, cwd=self.workdir
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
