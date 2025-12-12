from __future__ import annotations

from typing import Iterable, Optional

from loguru import logger

from src.service.jira.prompt_models import SubtaskPrompt

from .cli_executor import ClineExecutor
from .context_builder import JiraContextBuilder
from .models import OrchestrationResult, SubtaskPlan, TaskPayload
from .persistence import TaskPersistence
from .prompt_builder import PromptBuilder


class TaskOrchestrator:
    """Build prompts and execution plans, and run orchestration via the CLI."""

    def __init__(
        self,
        *,
        context_builder: JiraContextBuilder,
        prompt_builder: PromptBuilder,
        persistence: TaskPersistence,
        executor: Optional[ClineExecutor] = None,
    ) -> None:
        self._context_builder = context_builder
        self._prompt_builder = prompt_builder
        self._persistence = persistence
        self._executor = executor or ClineExecutor()

    async def orchestrate(self, payload: TaskPayload) -> OrchestrationResult:
        """Generate prompts + plan, persist them, and return a CLI-ready summary prompt."""

        if not self._executor.cli_available:
            raise RuntimeError("CLINE CLI binary is not available.")

        context = await self._context_builder.build(payload)

        # Ensure there is at least one prompt even when no subtasks exist.
        if not context.subtask_prompts:
            context.subtask_prompts.append(
                SubtaskPrompt(
                    key=payload.task_id,
                    summary="Full task",
                    description=context.detailed_description,
                    prompt=self._build_fallback_prompt(payload),
                )
            )

        await self._persistence.persist(context, payload)

        orchestration_prompt = self._prompt_builder.compose(context, payload)
        subtask_plans = self._map_subtasks(context.subtask_prompts)
        simple_prompt = self._build_simple_prompt(payload, subtask_plans)

        # Kick off the orchestration prompt through the CLINE CLI. This runs the
        # high-level planning prompt; detailed subtask prompts are persisted below.
        await self._executor.execute(orchestration_prompt, payload)

        logger.info(
            "Generated orchestration prompt for task '{task_id}':\n{prompt}",
            task_id=payload.task_id,
            prompt=orchestration_prompt,
        )

        return OrchestrationResult(
            task_id=payload.task_id,
            repo_url=payload.repo_url,
            base_branch=payload.base_branch,
            orchestration_prompt=orchestration_prompt,
            simple_prompt=simple_prompt,
            subtask_prompts=subtask_plans,
        )

    @staticmethod
    def _map_subtasks(subtasks: Iterable[SubtaskPrompt]) -> list[SubtaskPlan]:
        return [
            SubtaskPlan(
                subtask_key=sub.key,
                summary=sub.summary,
                description=sub.description,
                prompt=sub.prompt,
            )
            for sub in subtasks
            if sub.prompt
        ]

    @staticmethod
    def _build_simple_prompt(
        payload: TaskPayload, subtask_prompts: list[SubtaskPlan]
    ) -> str:
        """Short prompt the CLI can consume to produce an execution plan."""

        subtask_titles = ", ".join(
            filter(
                None,
                [
                    prompt.summary or prompt.subtask_key
                    for prompt in subtask_prompts
                    if prompt.prompt
                ],
            )
        )

        if not subtask_titles:
            subtask_titles = "Treat as a single work item."

        return (
            "You are the Task Orchestrator. Generate an execution plan and CLI-ready "
            "prompts for each subtask listed below. If no subtasks exist, treat the "
            "whole task as one subtask and produce a single implementation prompt.\n"
            f"Task ID: {payload.task_id}\n"
            f"Repository: {payload.repo_url}\n"
            f"Base branch: {payload.base_branch}\n"
            f"Subtasks: {subtask_titles}"
        )

    @staticmethod
    def _build_fallback_prompt(payload: TaskPayload) -> str:
        return (
            "No subtasks were provided. Create a full execution plan for the entire "
            "task, then implement it end-to-end. Focus on correctness and clear steps. "
            f"Task ID: {payload.task_id}, Repo: {payload.repo_url}, "
            f"Base branch: {payload.base_branch}."
        )


__all__ = ["TaskOrchestrator"]
