from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger

from src.core.config import settings
from src.service.database_handler.config import create_tables, get_db_session
from src.service.database_handler.crud import TaskCRUD
from src.service.database_handler.models.task import TaskStatus

from .cli_executor import ClineExecutor
from .models import TaskPayload
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

    @staticmethod
    def _extract_required_roles(rows: list[Any]) -> list[str]:
        """Extract required roles from DB rows (best-effort, schema-less)."""
        roles: set[str] = set()
        for row in rows:
            additional = getattr(row, "additional_json", None)
            if not isinstance(additional, dict):
                continue
            value = (
                additional.get("required_roles")
                or additional.get("roles")
                or additional.get("requiredRoles")
            )
            if isinstance(value, str):
                cleaned = value.strip()
                if cleaned:
                    roles.add(cleaned)
                continue
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        cleaned = item.strip()
                        if cleaned:
                            roles.add(cleaned)
        return sorted(roles)

    @staticmethod
    def _compose_execution_prompt(
        *, parent_prompt: str, subtask_prompt: str | None, subtask_key: str
    ) -> str:
        """Parent prompt must always be included for subtask executions."""
        child = (subtask_prompt or "").strip()
        return (
            f"=== PARENT TASK PROMPT ===\n{parent_prompt.strip()}\n\n"
            f"=== SUBTASK PROMPT ({subtask_key}) ===\n{child}"
        ).strip()

    async def start_task(
        self,
        *,
        task_key: str,
        repo_url: str | None = None,
        base_branch: str | None = None,
    ) -> list[str]:
        """Start execution by loading the task+subtasks from SQLite and running the plan.

        Prompt execution logic (strict):
        - Parent task prompt must always be included.
        - If subtasks exist: execute once per subtask (parent+subtask prompt).
        - If no subtasks exist: execute exactly once (parent prompt only).
        """

        if not self.cli_available:
            raise RuntimeError("CLINE CLI binary is not available.")

        create_tables()

        def _load_sync():
            db = get_db_session()
            try:
                parent = TaskCRUD.get_task_by_task_id(db, task_key)
                subtasks = TaskCRUD.get_subtasks_by_task_id(db, task_key)
                return parent, subtasks
            finally:
                db.close()

        parent, subtasks = await asyncio.to_thread(_load_sync)
        if parent is None:
            raise RuntimeError(f"Task '{task_key}' not found in DB.")

        parent_prompt = (parent.prompt or "").strip()
        if not parent_prompt:
            raise RuntimeError(
                f"Task '{task_key}' has no stored parent prompt to execute."
            )

        subtask_runs: list[dict[str, Any]] = []
        for st in subtasks or []:
            sub_key = (st.sub_task_id or "").strip()
            prompt = (st.prompt or "").strip()
            if not sub_key:
                raise RuntimeError(
                    f"Task '{task_key}' contains a malformed subtask row (missing sub_task_id)."
                )
            if not prompt:
                raise RuntimeError(
                    f"Subtask '{sub_key}' for task '{task_key}' has no stored prompt to execute."
                )
            subtask_runs.append(
                {"db_id": st.id, "subtask_key": sub_key, "subtask_prompt": prompt}
            )

        required_roles = self._extract_required_roles([parent, *list(subtasks or [])])
        if required_roles:
            logger.info(
                "Extracted required roles for task '{task_key}': {roles}",
                task_key=task_key,
                roles=", ".join(required_roles),
            )

        effective_repo_url = (
            getattr(parent, "repo_url", None) or repo_url or ""
        ).strip()
        effective_base_branch = (
            getattr(parent, "base_branch", None)
            or base_branch
            or settings.DEFAULT_BASE_BRANCH
        ).strip()

        if not effective_repo_url:
            raise RuntimeError(
                f"Task '{task_key}' has no repo_url available (neither in DB nor request)."
            )

        started_subtasks = (
            [r["subtask_key"] for r in subtask_runs] if subtask_runs else [task_key]
        )

        async def _run_plan_in_background() -> None:
            db = get_db_session()
            try:
                if subtask_runs:
                    collected: list[tuple[str, str | None]] = []
                    for run in subtask_runs:
                        sub_key = run["subtask_key"]
                        prompt = self._compose_execution_prompt(
                            parent_prompt=parent_prompt,
                            subtask_prompt=run["subtask_prompt"],
                            subtask_key=sub_key,
                        )
                        payload = TaskPayload(
                            task_id=sub_key,
                            repo_url=effective_repo_url,
                            base_branch=effective_base_branch,
                        )
                        summary = await self._executor.execute(prompt, payload)
                        TaskCRUD.update_task(
                            db,
                            run["db_id"],
                            agent_summary=summary,
                            status=TaskStatus.SUCCESS.value,
                        )
                        collected.append((sub_key, summary))

                    combined = "\n\n".join(
                        (
                            f"## {sub_key}\n{(summary or '').strip()}"
                            if (summary or "").strip()
                            else f"## {sub_key}\n(no summary)"
                        )
                        for sub_key, summary in collected
                    ).strip()
                    TaskCRUD.update_task(
                        db,
                        parent.id,
                        agent_summary=combined or None,
                        status=TaskStatus.SUCCESS.value,
                    )
                else:
                    payload = TaskPayload(
                        task_id=task_key,
                        repo_url=effective_repo_url,
                        base_branch=effective_base_branch,
                    )
                    summary = await self._executor.execute(parent_prompt, payload)
                    TaskCRUD.update_task(
                        db,
                        parent.id,
                        agent_summary=summary,
                        status=TaskStatus.SUCCESS.value,
                    )
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "Task execution failed for '{task_key}': {error}",
                    task_key=task_key,
                    error=exc,
                )
                try:
                    TaskCRUD.update_task(
                        db,
                        parent.id,
                        agent_summary=str(exc),
                        status=TaskStatus.FAILED.value,
                    )
                except Exception:  # noqa: BLE001
                    logger.exception(
                        "Failed to mark task '{task_key}' as FAILED after execution error.",
                        task_key=task_key,
                    )
            finally:
                db.close()

        asyncio.create_task(_run_plan_in_background(), name=f"task-exec-{task_key}")
        return started_subtasks

    async def start_from_store(self, task_key: str) -> list[str]:
        """Backwards-compatible alias for `start_task`."""
        return await self.start_task(task_key=task_key)


__all__ = ["TaskExecutor"]
