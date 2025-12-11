from __future__ import annotations

import asyncio

from loguru import logger

from src.core.config import settings

from .cli_executor import ClineExecutor
from .models import StoredTaskPlan, SubtaskPlan, TaskPayload
from .persistence import TaskPersistence


class TaskExecutor:
    """Execute stored task/subtask prompts via the CLINE CLI."""

    def __init__(
        self,
        *,
        executor: ClineExecutor | None = None,
        persistence: TaskPersistence,
    ) -> None:
        self._executor = executor or ClineExecutor(
            settings.CLINE_CLI_BIN,
            settings.CLINE_CLI_ARGS,
            settings.TASK_WORKDIR,
        )
        self._persistence = persistence

    @property
    def cli_available(self) -> bool:
        return self._executor.cli_available

    async def start_from_store(self, task_key: str) -> list[str]:
        """Launch CLI executions sequentially using stored prompts."""

        if not self.cli_available:
            raise RuntimeError("CLINE CLI binary is not available.")

        plan: StoredTaskPlan | None = await self._persistence.load_plan(task_key)
        if plan is None:
            raise RuntimeError(f"No stored prompts found for task '{task_key}'.")

        prompts = plan.subtask_prompts or [self._build_fallback_subtask(task_key, plan)]

        base_branch = plan.base_branch or settings.DEFAULT_BASE_BRANCH
        subtask_identifiers = [
            prompt.subtask_key or f"{task_key}-subtask-{index + 1}"
            for index, prompt in enumerate(prompts)
        ]

        async def _run_plan() -> None:
            for index, prompt in enumerate(prompts):
                subtask_id = subtask_identifiers[index]

                payload = TaskPayload(
                    task_id=subtask_id,
                    repo_url=plan.repo_url,
                    base_branch=base_branch,
                )

                logger.info(
                    "Starting stored subtask '{subtask_id}' for task '{task_key}'.",
                    subtask_id=subtask_id,
                    task_key=task_key,
                )
                await self._executor.execute(prompt.prompt, payload)

        asyncio.create_task(_run_plan(), name=f"task-executor-{task_key}")
        return subtask_identifiers

    @staticmethod
    def _build_fallback_subtask(task_key: str, plan: StoredTaskPlan) -> SubtaskPlan:
        fallback_prompt = (
            "No subtasks were stored. Execute the full task end-to-end using the "
            "available context. Ensure correctness and summarize outcomes."
        )
        return SubtaskPlan(
            subtask_key=task_key,
            summary="Full task",
            description=plan.detailed_description,
            prompt=fallback_prompt,
        )


__all__ = ["TaskExecutor"]
