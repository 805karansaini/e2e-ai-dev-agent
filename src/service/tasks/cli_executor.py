from __future__ import annotations

import logging
import os
import shutil
from asyncio.subprocess import PIPE, create_subprocess_exec
from typing import Optional

from .models import TaskPayload

logger = logging.getLogger(__name__)


class ClineExecutor:
    """Execute the CLINE CLI with a prepared prompt."""

    def __init__(
        self,
        cli_bin: str,
        extra_args: Optional[list[str]] = None,
        workdir: Optional[str] = None,
    ) -> None:
        self.cli_bin = cli_bin
        self.extra_args = extra_args or []
        self.workdir = workdir

    @property
    def cli_available(self) -> bool:
        return shutil.which(self.cli_bin) is not None

    async def execute(self, prompt: str, payload: TaskPayload) -> None:
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
            "-y",
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


__all__ = ["ClineExecutor"]
