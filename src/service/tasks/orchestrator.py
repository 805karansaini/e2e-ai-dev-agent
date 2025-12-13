from __future__ import annotations

import json
from typing import Iterable, Optional

from loguru import logger

from src.core.config import settings

from .cli_executor import ClineExecutor
from .models import (
    DbTaskContext,
    OrchestratedPromptOutput,
    OrchestrationResult,
    SubtaskPlan,
    TaskPayload,
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

        orchestration_prompt = self._prompt_builder.compose(context, payload)
        logger.debug(
            "Generated orchestration prompt for task '{task_id}':\n{prompt}",
            task_id=payload.task_id,
            prompt=orchestration_prompt,
        )

        orchestration_preamble = self._prompt_builder.orchestration_preamble()
        orchestration_context = self._prompt_builder.compose(
            context, payload, include_orchestration_preamble=False
        )

        structured = await self._generate_high_level_plan_via_openrouter(
            prompt=orchestration_context,
            system_preamble=orchestration_preamble,
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

        subtask_plans = self._build_subtask_plans_from_db_context(
            context=context,
            payload=payload,
            parent_prompt=parent_prompt,
            subtask_prompt_map=subtask_prompt_map,
        )

        logger.debug(f"Subtask plans: {subtask_plans}")

        simple_prompt = self._build_simple_prompt(payload, subtask_plans)
        logger.debug(f"Simple prompt: {simple_prompt}")

        if use_cline:
            # Kick off the orchestration prompt through the CLINE CLI. This runs the
            # high-level planning prompt; per-item prompts are persisted above.
            await self._executor.execute(orchestration_prompt, payload)

        return OrchestrationResult(
            task_id=payload.task_id,
            repo_url=payload.repo_url,
            base_branch=payload.base_branch,
            orchestration_prompt=orchestration_prompt,
            simple_prompt=simple_prompt,
            subtask_prompts=subtask_plans,
        )

    @staticmethod
    def _ensure_additional_properties_false(schema: dict) -> None:
        """Recursively ensure all object schemas have additionalProperties: false."""
        if isinstance(schema, dict):
            # Special handling for OrchestratedPromptItem
            if schema.get("title") == "OrchestratedPromptItem":
                schema["additionalProperties"] = False
                # Azure requires all properties to be in required array when additionalProperties is false
                if "required" in schema:
                    all_props = set(schema.get("properties", {}).keys())
                    current_required = set(schema["required"])
                    missing = all_props - current_required
                    if missing:
                        schema["required"].extend(list(missing))
            # For other object types, just set additionalProperties to false
            elif schema.get("type") == "object" and "properties" in schema:
                schema["additionalProperties"] = False

            # Recursively process all nested schemas
            for key, value in schema.items():
                if isinstance(value, (dict, list)):
                    if isinstance(value, list):
                        for item in value:
                            TaskOrchestrator._ensure_additional_properties_false(item)
                    else:
                        TaskOrchestrator._ensure_additional_properties_false(value)

    @staticmethod
    async def _generate_high_level_plan_via_openrouter(
        *,
        prompt: str,
        system_preamble: str,
        context: DbTaskContext,
        payload: TaskPayload,
    ) -> OrchestratedPromptOutput:
        """Call OpenRouter to return structured prompts (task + subtasks).

        This uses OpenAI's `response_format: json_schema` so the model returns
        machine-insertable output for the database.
        """

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

        schema = OrchestratedPromptOutput.model_json_schema()
        # Ensure additionalProperties is set to false recursively for strict schema validation
        TaskOrchestrator._ensure_additional_properties_false(schema)

        work_items_lines: list[str] = []
        work_items_lines.append(f"- TASK: task_id={context.task_id} (sub_task_id=null)")
        for st in context.subtasks or []:
            if not st.key:
                continue
            work_items_lines.append(
                f"- SUBTASK: task_id={context.task_id}, sub_task_id={st.key}"
            )

        subtasks_exist = any(st.key for st in (context.subtasks or []))
        behavior_note = (
            "There are NO subtasks. Return exactly 1 prompt item for the TASK. "
            "That TASK prompt must be an implementation prompt for the full task."
            if not subtasks_exist
            else "Subtasks exist. Return 1 TASK prompt (overall context/overview) "
            "and 1 prompt per SUBTASK (implementation prompts)."
        )

        schema_guard = (
            "Return ONLY valid JSON that strictly conforms to this JSON Schema:\n"
            f"{json.dumps(schema)}\n"
            "Do not add extra fields. Do not include prose."
        )
        system_prompt = "\n\n".join(
            [schema_guard.strip(), (system_preamble or "").strip()]
        ).strip()

        resp = await client.chat.completions.create(
            model=settings.OPENROUTER_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": (
                        "You are the Task Orchestrator.\n\n"
                        "Goal: generate N prompts to persist into the database.\n"
                        f"N = 1 + number_of_subtasks_for_task_id={context.task_id}\n"
                        f"{behavior_note}\n\n"
                        "Work items (MUST match exactly, do not invent new IDs):\n"
                        + "\n".join(work_items_lines)
                        + "\n\n"
                        "Repository context:\n"
                        f"- repo_url: {payload.repo_url}\n"
                        f"- base_branch: {payload.base_branch}\n\n"
                        "Context:\n" + prompt
                    ),
                },
            ],
            temperature=0,
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "OrchestratedPromptOutput", "schema": schema},
            },
        )

        content = (resp.choices[0].message.content or "").strip()
        if not content:
            raise RuntimeError("OpenRouter returned an empty completion.")
        try:
            return OrchestratedPromptOutput.model_validate_json(content)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "OpenRouter returned a response that did not match the expected schema."
            ) from exc

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
        structured: OrchestratedPromptOutput,
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
            and (it.sub_task_id is None or it.sub_task_id == "")
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
