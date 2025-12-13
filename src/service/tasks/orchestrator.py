from __future__ import annotations

from typing import Optional

from loguru import logger

from src.core.config import settings
from src.service.llm import OpenRouterLLM

from .cli_executor import ClineExecutor
from .models import (
    DbTaskContext,
    OrchestrationResult,
    SubtaskPlan,
    TaskPayload,
    TaskPromptOutput,
)
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
        logger.debug(f"Context: {context}")

        # System prompt for the orchestrator model.
        orchestration_preamble = self._prompt_builder.orchestration_preamble()

        # Context for the orchestrator model.
        orchestration_context = self._prompt_builder.compose(
            context, payload, include_orchestration_preamble=False
        )
        logger.debug(f"Orchestration context: {orchestration_context}")

        structured = await self._generate_high_level_plan_via_openrouter(
            system_preamble=orchestration_preamble,
            prompt=orchestration_context,
            context=context,
            payload=payload,
        )

        logger.debug(f"Structured: {structured}")

        parent_prompt, subtask_prompt_map = self._validate_and_extract_prompts(
            structured=structured, context=context, payload=payload
        )
        logger.debug(f"Parent prompt: {parent_prompt}")
        logger.debug(f"Subtask prompt map: {subtask_prompt_map}")

        await self._persistence.persist_orchestration_prompts(
            task_key=payload.task_id,
            parent_prompt=parent_prompt,
            subtask_prompts=subtask_prompt_map,
            payload=payload,
        )

        # TODO: Remove later
        # subtask_plans = self._build_subtask_plans_from_db_context(
        #     context=context,
        #     payload=payload,
        #     parent_prompt=parent_prompt,
        #     subtask_prompt_map=subtask_prompt_map,
        # )

        # logger.debug(f"Subtask plans: {subtask_plans}")

        # simple_prompt = self._build_simple_prompt(payload, subtask_plans)
        # logger.debug(f"Simple prompt: {simple_prompt}")

        # orchestration_prompt = parent_prompt

        # if use_cline:
        #     # Kick off the orchestration prompt through the CLINE CLI. This runs the
        #     # high-level planning prompt; per-item prompts are persisted above.
        #     await self._executor.execute(orchestration_prompt, payload)

        orchestration_prompt = ""
        simple_prompt = ""
        subtask_plans = []

        return OrchestrationResult(
            task_id=payload.task_id,
            repo_url=payload.repo_url,
            base_branch=payload.base_branch,
            orchestration_prompt=orchestration_prompt,
            simple_prompt=simple_prompt,
            subtask_prompts=subtask_plans,
        )

    @staticmethod
    async def _generate_high_level_plan_via_openrouter(
        *,
        system_preamble: str,
        prompt: str,
        context: DbTaskContext,
        payload: TaskPayload,
    ) -> TaskPromptOutput:
        """Call OpenRouter to return structured prompts (task + subtasks).

        This uses OpenAI's `response_format: json_schema` so the model returns
        machine-insertable output for the database.
        """
        system_prompt = system_preamble

        work_items_lines: list[str] = []
        work_items_lines.append(f"- TASK: task_id={context.task_id} (sub_task_id=null)")
        for st in context.subtasks or []:
            if not st.key:
                continue
            work_items_lines.append(
                f"- SUBTASK: task_id={context.task_id}, sub_task_id={st.key}"
            )

        subtasks_exist = any(st.key for st in (context.subtasks or []))

        if not subtasks_exist:
            behavior_note = (
                "NO SUBTASKS EXIST.\n"
                "Generate exactly 1 prompt for the TASK that:\n"
                "- Is directly executable by a CLI agent\n"
                "- Focuses on WHAT to implement, not HOW (let the agent decide implementation details)\n"
                "- Remains concise (2-4 sentences)"
            )
        else:
            behavior_note = (
                "SUBTASKS EXIST.\n"
                "Generate exactly 1 TASK prompt + 1 prompt per SUBTASK:\n\n"
                "TASK prompt (non-executable high-level summary of task and subtasks):\n"
                "- Describe the overall objective and how subtasks relate\n"
                "- Specify critical constraints, dependencies, or ordering requirements\n"
                "- Do NOT provide implementation steps\n"
                "- Keep to 3-5 sentences\n\n"
                "SUBTASK prompts (executable units):\n"
                "- Each must be independently executable by a CLI agent\n"
                "- Focus on WHAT to implement for that specific subtask\n"
                "- Include acceptance criteria specific to the subtask\n"
                "- Reference parent task context only when necessary\n"
                "- Do NOT provide implementation steps\n"
                "- Keep each to 2-4 sentences"
            )

        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": (
                    "Generate structured prompts for database persistence.\n"
                    f"Required: 1 TASK prompt + {len([w for w in work_items_lines if 'SUBTASK' in w])} SUBTASK prompt(s)\n"
                    f"Task ID: {context.task_id}\n\n"
                    f"{behavior_note}\n\n"
                    "=== CRITICAL REQUIREMENTS ===\n"
                    "1. EXACT ID MATCHING: Use only the work item IDs listed below. Never invent or modify IDs.\n"
                    "2. IMPLEMENTATION FOCUS: Prompts should specify WHAT needs to be done, not HOW to do it.\n"
                    "4. NO ASSUMPTIONS: Don't add dependencies, tools, or services not mentioned in the context.\n"
                    "5. CLARITY OVER LENGTH: Shorter, clearer prompts are better than verbose ones.\n\n"
                    "=== WORK ITEMS (use these IDs exactly) ===\n"
                    + "\n".join(work_items_lines)
                    + "\n\n"
                    "=== REPOSITORY INFO ===\n"
                    f"Repository: {payload.repo_url}\n"
                    f"Base Branch: {payload.base_branch}\n\n"
                    "=== TASK CONTEXT ===\n" + prompt + "\n\n"
                    "Generate prompts that are:\n"
                    "- Actionable: Clear about what success looks like\n"
                    "- Minimal: No redundant information from context\n"
                    "- Scoped: Each subtask prompt is independently completable\n"
                    "- Verifiable: Includes concrete acceptance criteria"
                ),
            },
        ]

        llm = OpenRouterLLM.from_settings()
        return await llm.chat_json_schema(
            messages=messages,
            response_model=TaskPromptOutput,
            schema_name="TaskPromptOutput",
        )

    @staticmethod
    def _build_subtask_plans_from_db_context(
        *,
        context: DbTaskContext,
        payload: TaskPayload,
        parent_prompt: str,
        subtask_prompt_map: dict[str, str],
    ) -> list[SubtaskPlan]:
        # API response should always include at least one "work item" prompt.
        subtasks = [st for st in (context.subtasks or []) if st.key]
        if not subtasks:
            return [
                SubtaskPlan(
                    subtask_key=payload.task_id,
                    summary=context.summary or "Full task",
                    description=context.description,
                    prompt=parent_prompt,
                )
            ]

        plans: list[SubtaskPlan] = []
        for st in subtasks:
            prompt = (subtask_prompt_map.get(st.key) or "").strip()
            if not prompt:
                continue
            plans.append(
                SubtaskPlan(
                    subtask_key=st.key,
                    summary=st.summary,
                    description=st.description,
                    prompt=prompt,
                )
            )
        return plans

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
    def _validate_and_extract_prompts(
        *,
        structured: TaskPromptOutput,
        context: DbTaskContext,
        payload: TaskPayload,
    ) -> tuple[str, dict[str, str]]:
        expected_subtask_keys = [st.key for st in (context.subtasks or []) if st.key]
        expected_total = 1 + len(expected_subtask_keys)

        items = structured.prompts or []
        if len(items) != expected_total:
            raise RuntimeError(
                f"OpenRouter returned {len(items)} prompt items, expected {expected_total}."
            )

        parent_candidates = [
            it
            for it in items
            if it.task_type == "TASK"
            and it.task_id == payload.task_id
            and it.sub_task_id is None
        ]
        if len(parent_candidates) != 1:
            raise RuntimeError("OpenRouter must return exactly one TASK prompt item.")
        parent_prompt = (parent_candidates[0].prompt or "").strip()
        if not parent_prompt:
            raise RuntimeError("TASK prompt is empty.")

        subtask_map: dict[str, str] = {}
        for it in items:
            if it.task_type != "SUBTASK":
                continue
            if it.task_id != payload.task_id:
                raise RuntimeError(
                    f"SUBTASK prompt has unexpected task_id '{it.task_id}'."
                )
            sub_id = (it.sub_task_id or "").strip()
            if sub_id not in expected_subtask_keys:
                raise RuntimeError(
                    f"SUBTASK prompt returned unknown sub_task_id '{sub_id}'."
                )
            if sub_id in subtask_map:
                raise RuntimeError(f"Duplicate SUBTASK prompt for '{sub_id}'.")
            pr = (it.prompt or "").strip()
            if not pr:
                raise RuntimeError(f"SUBTASK prompt for '{sub_id}' is empty.")
            subtask_map[sub_id] = pr

        if expected_subtask_keys:
            missing = [k for k in expected_subtask_keys if k not in subtask_map]
            if missing:
                raise RuntimeError(
                    f"OpenRouter did not return prompts for subtasks: {', '.join(missing)}"
                )

        return parent_prompt, subtask_map


__all__ = ["TaskOrchestrator"]
