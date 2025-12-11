from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Optional

from loguru import logger

from src.core.config import settings

from .cli_executor import ClineExecutor
from .context_builder import JiraContextBuilder
from .models import TaskPayload
from .persistence import TaskPersistence
from .prompt_builder import PromptBuilder


class TaskRunner:
    """Async task runner that orchestrates fetching context and executing CLINE."""

    def __init__(
        self,
        cli_bin: str,
        extra_args: Optional[list[str]] = None,
        workdir: Optional[str] = None,
        db_path: Optional[str] = None,
        *,
        context_builder: JiraContextBuilder | None = None,
        prompt_builder: PromptBuilder | None = None,
        executor: ClineExecutor | None = None,
        persistence: TaskPersistence | None = None,
    ) -> None:
        self.cli_bin = cli_bin
        self.extra_args = extra_args or []
        self.workdir = workdir

        self.base_dir = Path(workdir or os.getcwd())
        self.attachments_dir = self.base_dir / "data" / "jira_attachments"
        self.db_path = Path(db_path) if db_path else self.base_dir / "data" / "tasks.db"

        self._context_builder = context_builder or JiraContextBuilder(
            self.attachments_dir
        )
        self._prompt_builder = prompt_builder or PromptBuilder(
            self.base_dir, self.attachments_dir
        )
        self._executor = executor or ClineExecutor(cli_bin, self.extra_args, workdir)
        self._persistence = persistence or TaskPersistence(
            self.db_path, self.attachments_dir
        )

        self._queue: asyncio.Queue[TaskPayload] | None = None
        self._worker: asyncio.Task[None] | None = None
        self._started = False

    @property
    def cli_available(self) -> bool:
        return self._executor.cli_available

    @property
    def is_running(self) -> bool:
        return self._started and self._worker is not None and not self._worker.done()

    @property
    def queued_tasks(self) -> int:
        return self._queue.qsize() if self._queue else 0

    async def start(self) -> None:
        if self._started:
            return

        self._queue = asyncio.Queue()
        self._started = True
        self._worker = asyncio.create_task(self._worker_loop(), name="task-runner")
        logger.info(
            "Task runner started with CLI bin '{cli_bin}'.", cli_bin=self.cli_bin
        )

    async def stop(self) -> None:
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
        if not self._started or self._queue is None:
            raise RuntimeError("Task runner is not started.")

        await self._queue.put(payload)
        logger.info(
            "Enqueued task '{task_id}' for repo '{repo}' (branch={branch}).",
            task_id=payload.task_id,
            repo=payload.repo_url,
            branch=payload.base_branch,
        )

    async def _worker_loop(self) -> None:
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
                    "Failed to execute CLINE task '{task_id}': {error}",
                    task_id=payload.task_id,
                    error=exc,
                )
            finally:
                queue.task_done()

    async def _run_task(self, payload: TaskPayload) -> None:
        context = await self._context_builder.build(payload)
        await self._persistence.persist(context, payload)
        prompt = self._prompt_builder.compose(context, payload)
        await self._executor.execute(prompt, payload)


# Shared task runner instance configured from settings
task_runner = TaskRunner(
    cli_bin=settings.CLINE_CLI_BIN,
    extra_args=settings.CLINE_CLI_ARGS,
    workdir=settings.TASK_WORKDIR,
)


__all__ = ["TaskPayload", "TaskRunner", "task_runner"]
