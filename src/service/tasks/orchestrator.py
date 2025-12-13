from __future__ import annotations

from textwrap import dedent
from typing import Iterable, Optional

from loguru import logger

from src.core.config import settings
from src.service.jira.prompt_models import SubtaskPrompt

from .cli_executor import ClineExecutor
from .models import DbTaskContext, OrchestrationResult, SubtaskPlan, TaskPayload
from .persistence import TaskPersistence
from .prompt_builder import PromptBuilder


class TaskOrchestrator:
    """Build prompts and execution plans, and optionally run high-level planning."""

    def __init__(
        self,
        *,
        prompt_builder: PromptBuilder,
        persistence: TaskPersistence,
        executor: Optional[ClineExecutor] = None,
    ) -> None:
        self._prompt_builder = prompt_builder
        self._persistence = persistence
        self._executor = executor or ClineExecutor(
            settings.CLINE_CLI_BIN, settings.CLINE_CLI_ARGS, settings.TASK_WORKDIR
        )

    async def orchestrate(
        self, payload: TaskPayload, *, use_cline: bool = False
    ) -> OrchestrationResult:
        """Generate prompts + plan, persist them, and optionally run high-level planning.

        - When `use_cline=True`, runs the orchestration prompt through the local CLINE CLI.
        - When `use_cline=False` (default), calls OpenRouter (OpenAI-compatible) to produce
          a high-level plan; this plan is logged but not returned (to keep return models unchanged).
        """

        if use_cline and not self._executor.cli_available:
            raise RuntimeError("CLINE CLI binary is not available.")

        context = await self._persistence.load_task_context(payload.task_id)
        if context is None:
            raise RuntimeError(
                f"Task '{payload.task_id}' not found in DB. Import it first."
            )

        # Build execution prompts for each subtask; if no subtasks exist, treat
        # the parent task as a single work item and store the prompt on the parent.
        subtask_prompts: list[SubtaskPrompt] = []
        for st in context.subtasks or []:
            if not st.key:
                continue
            subtask_prompts.append(
                SubtaskPrompt(
                    key=st.key,
                    summary=st.summary,
                    description=st.description,
                    prompt=self._compose_db_subtask_prompt(
                        context, st.key, st.summary, st.description
                    ),
                )
            )

        has_subtasks = bool(subtask_prompts)
        # Always generate a parent-task prompt as well (stored on TASK row).
        parent_prompt: str | None = self._compose_db_task_prompt(
            context, payload, has_subtasks=has_subtasks
        )
        if not has_subtasks:
            # Preserve prior behavior: surface at least one prompt in the response,
            # but do NOT persist this as a SUBTASK row (it's stored on the parent task).
            subtask_prompts.append(
                SubtaskPrompt(
                    key=payload.task_id,
                    summary="Full task",
                    description=context.description,
                    prompt=parent_prompt,
                )
            )

        await self._persistence.persist_orchestration_prompts(
            task_key=payload.task_id,
            parent_prompt=parent_prompt,
            subtask_prompts={sp.key: sp.prompt for sp in subtask_prompts if sp.prompt},
            payload=payload,
        )

        orchestration_prompt = self._prompt_builder.compose(context, payload)
        subtask_plans = self._map_subtasks(subtask_prompts)
        simple_prompt = self._build_simple_prompt(payload, subtask_plans)

        logger.debug(
            "Generated orchestration prompt for task '{task_id}':\n{prompt}",
            task_id=payload.task_id,
            prompt=orchestration_prompt,
        )

        if use_cline:
            # Kick off the orchestration prompt through the CLINE CLI. This runs the
            # high-level planning prompt; detailed subtask prompts are persisted above.
            await self._executor.execute(orchestration_prompt, payload)
        else:
            high_level_plan = await self._generate_high_level_plan_via_openrouter(
                prompt=orchestration_prompt
            )
            logger.info(
                "Generated high-level plan via OpenRouter for task '{task_id}':\n{plan}\n\n",
                task_id=payload.task_id,
                plan=high_level_plan,
            )

        # TODO INSERT THAT PROMPTS FOR TASK AND SUBTASKS INTO THE DATABASE
        return OrchestrationResult(
            task_id=payload.task_id,
            repo_url=payload.repo_url,
            base_branch=payload.base_branch,
            orchestration_prompt=orchestration_prompt,
            simple_prompt=simple_prompt,
            subtask_prompts=subtask_plans,
        )

    @staticmethod
    async def _generate_high_level_plan_via_openrouter(*, prompt: str) -> str:
        """Call OpenRouter using the OpenAI Python SDK (OpenAI-compatible endpoint)."""

        api_key = settings.OPENROUTER_API_KEY.strip()

        try:
            from openai import AsyncOpenAI  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "openai Python package is not installed. Add `openai` to requirements "
                "and install dependencies to enable OpenRouter calls."
            ) from exc

        default_headers: dict[str, str] = {}
        if settings.OPENROUTER_HTTP_REFERER.strip():
            default_headers["HTTP-Referer"] = settings.OPENROUTER_HTTP_REFERER
        if settings.OPENROUTER_APP_TITLE.strip():
            default_headers["X-Title"] = settings.OPENROUTER_APP_TITLE

        client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers=default_headers or None,
            timeout=settings.OPENROUTER_TIMEOUT_SECONDS,
        )

        resp = await client.chat.completions.create(
            model=settings.OPENROUTER_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )

        content = (resp.choices[0].message.content or "").strip()
        if not content:
            raise RuntimeError("OpenRouter returned an empty completion.")
        return content

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

    @staticmethod
    def _compose_db_subtask_prompt(
        context: DbTaskContext,
        subtask_key: str,
        subtask_summary: str | None,
        subtask_description: str | None,
    ) -> str:
        parent_summary = context.summary or context.task_id
        parent_description = (context.description or "No description provided.").strip()
        sub_summary = subtask_summary or "No summary"
        sub_description = (subtask_description or "No description provided.").strip()

        return dedent(
            f"""
            Parent task {context.task_id}: {parent_summary}
            Parent description:
            {parent_description}

            Subtask {subtask_key}: {sub_summary}
            Details:
            {sub_description}
            """
        ).strip()

    def _compose_db_task_prompt(
        self, context: DbTaskContext, payload: TaskPayload, *, has_subtasks: bool
    ) -> str:
        """Prompt to persist on the parent TASK row.

        - When subtasks exist, this is a parent-context prompt (not a subtask execution prompt).
        - When subtasks do not exist, this becomes the execution prompt for the whole task.
        """
        description = (context.description or "No description provided.").strip()
        if has_subtasks:
            base = (
                "This is the parent task context. Use it for overall alignment and "
                "to understand requirements. Do not implement individual subtasks "
                "from this prompt; each subtask has its own implementation prompt."
            )
        else:
            base = self._build_fallback_prompt(payload)
        return dedent(
            f"""
            {base}

            Task {context.task_id}: {context.summary or context.task_id}
            Details:
            {description}
            """
        ).strip()


__all__ = ["TaskOrchestrator"]
