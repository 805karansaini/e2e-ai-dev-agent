from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger

from src.core.config import settings
from src.service.database_handler.config import create_tables, get_db_session
from src.service.database_handler.crud import TaskCRUD
from src.service.database_handler.models.task import Task, TaskStatus, TaskType

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
        self._worker_task: asyncio.Task[None] | None = None
        self._execution_lock = asyncio.Lock()

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

        # NOTE: start_task() is intentionally lightweight.
        # It only marks the task (and any subtasks) as QUEUED.
        # The background worker is responsible for validating prompts/repo_url and executing.

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

        started_subtasks = [
            st.sub_task_id for st in (subtasks or []) if st.sub_task_id
        ] or [task_key]

        def _mark_queued_sync() -> None:
            db = get_db_session()
            try:
                # Parent always exists here.
                TaskCRUD.update_task(db, parent.id, status=TaskStatus.QUEUED.value)
                # Keep repo fields in sync with the request (so the worker can execute without request context).
                if effective_repo_url or effective_base_branch:
                    TaskCRUD.update_task(
                        db,
                        parent.id,
                        repo_url=effective_repo_url or None,
                        base_branch=effective_base_branch or None,
                    )

                # Mark subtasks as QUEUED too (sequential execution, no parallelism).
                for st in subtasks or []:
                    TaskCRUD.update_task(db, st.id, status=TaskStatus.QUEUED.value)
            finally:
                db.close()

        # Mark QUEUED immediately after validations pass (before background execution).
        await asyncio.to_thread(_mark_queued_sync)

        # Ensure the single background worker is running (it will pick up queued tasks).
        self._ensure_worker_started()
        return started_subtasks

    def _ensure_worker_started(self) -> None:
        """Start exactly one worker loop responsible for executing queued parent tasks."""
        if self._worker_task and not self._worker_task.done():
            return
        self._worker_task = asyncio.create_task(
            self._worker_loop(), name="task-exec-worker"
        )

    async def _worker_loop(self) -> None:
        """Single worker: executes at most one parent task (and its subtasks) at a time."""
        while True:
            try:
                next_task_key = await asyncio.to_thread(self._next_queued_parent_task)
                if not next_task_key:
                    # No queued tasks right now; poll again shortly.
                    await asyncio.sleep(1.0)
                    continue

                # Only one parent task (and its subtasks) may run at any time.
                async with self._execution_lock:
                    await self._execute_parent_task(next_task_key)
            except Exception:  # noqa: BLE001
                logger.exception("Task execution worker crashed; continuing.")
                await asyncio.sleep(1.0)

    def _next_queued_parent_task(self) -> str | None:
        """Return the next QUEUED parent task_id (TASK row only), or None."""
        db = get_db_session()
        try:
            row = (
                db.query(Task)
                .filter(Task.task_type == TaskType.TASK)
                .filter(Task.sub_task_id.is_(None))
                .filter(Task.status == TaskStatus.QUEUED)
                .order_by(Task.created_at.asc(), Task.id.asc())
                .first()
            )
            return (row.task_id if row else None) or None
        finally:
            db.close()

    async def _review_code(self, *, task_key: str, payload: TaskPayload) -> None:
        """Background follow-up: ask the agent to review changes.

        Intentionally does NOT write anything back to the database.
        """
        template = self._load_prompt_template("high_level_review.md")
        prompt = f"Review\n\n{template}"
        logger.info(
            "Starting background review for task '{task_key}'.", task_key=task_key
        )
        await self._executor.execute(prompt, payload)

    async def _raise_pull_request(self, *, task_key: str, payload: TaskPayload) -> None:
        """Background follow-up: ask the agent to create a PR.

        Intentionally does NOT write anything back to the database.
        """
        template = self._load_prompt_template("create_pull_request.md")
        prompt = f"PR\n\n{template}"
        logger.info(
            "Starting background PR creation for task '{task_key}'.", task_key=task_key
        )
        await self._executor.execute(prompt, payload)

    async def _execute_parent_task(self, task_key: str) -> None:
        """Execute a single parent task and all its subtasks serially (no parallelism)."""

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
            return

        parent_prompt = (parent.prompt or "").strip()
        effective_repo_url = (getattr(parent, "repo_url", None) or "").strip()
        effective_base_branch = (
            getattr(parent, "base_branch", None) or settings.DEFAULT_BASE_BRANCH
        ).strip()

        db = get_db_session()
        try:
            # Validate prerequisites.
            if not effective_repo_url or not parent_prompt:
                TaskCRUD.update_task(
                    db,
                    parent.id,
                    agent_summary="Missing repo_url or parent prompt; cannot execute.",
                    status=TaskStatus.FAILURE.value,
                )
                return

            # Mark parent running.
            TaskCRUD.update_task(db, parent.id, status=TaskStatus.IN_PROGRESS.value)

            sub_rows = list(subtasks or [])
            if sub_rows:
                collected: list[tuple[str, str | None]] = []
                for st in sub_rows:
                    sub_key = (st.sub_task_id or "").strip()
                    sub_prompt = (st.prompt or "").strip()
                    if not sub_key or not sub_prompt:
                        TaskCRUD.update_task(
                            db,
                            parent.id,
                            agent_summary="Malformed subtask row (missing id/prompt).",
                            status=TaskStatus.FAILURE.value,
                        )
                        return

                    TaskCRUD.update_task(db, st.id, status=TaskStatus.IN_PROGRESS.value)

                    exec_prompt = self._compose_execution_prompt(
                        parent_prompt=parent_prompt,
                        subtask_prompt=sub_prompt,
                        subtask_key=sub_key,
                    )
                    payload = TaskPayload(
                        task_id=sub_key,
                        repo_url=effective_repo_url,
                        base_branch=effective_base_branch,
                    )
                    try:
                        summary = await self._executor.execute(exec_prompt, payload)
                    except Exception as exc:  # noqa: BLE001
                        TaskCRUD.update_task(
                            db,
                            st.id,
                            agent_summary=str(exc),
                            status=TaskStatus.FAILURE.value,
                        )
                        TaskCRUD.update_task(
                            db,
                            parent.id,
                            agent_summary=str(exc),
                            status=TaskStatus.FAILURE.value,
                        )
                        return

                    TaskCRUD.update_task(
                        db,
                        st.id,
                        agent_summary=summary,
                        status=TaskStatus.DONE.value,
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
                    status=TaskStatus.REVIEWING.value,
                )
            else:
                # No subtasks: run parent prompt exactly once.
                payload = TaskPayload(
                    task_id=task_key,
                    repo_url=effective_repo_url,
                    base_branch=effective_base_branch,
                )
                try:
                    summary = await self._executor.execute(parent_prompt, payload)
                except Exception as exc:  # noqa: BLE001
                    TaskCRUD.update_task(
                        db,
                        parent.id,
                        agent_summary=str(exc),
                        status=TaskStatus.FAILURE.value,
                    )
                    return
                TaskCRUD.update_task(
                    db,
                    parent.id,
                    agent_summary=summary,
                    status=TaskStatus.REVIEWING.value,
                )
            # Review + PR (background follow-ups; no DB writes).
            followup_payload = TaskPayload(
                task_id=task_key,
                repo_url=effective_repo_url,
                base_branch=effective_base_branch,
            )
            try:
                await self._review_code(task_key=task_key, payload=followup_payload)
            except Exception:  # noqa: BLE001
                logger.exception(
                    "Background review failed for task '{task_key}'.", task_key=task_key
                )
            TaskCRUD.update_task(db, parent.id, status=TaskStatus.PULL_REQUEST.value)

            try:
                await self._raise_pull_request(
                    task_key=task_key, payload=followup_payload
                )
            except Exception:  # noqa: BLE001
                logger.exception(
                    "Background PR creation failed for task '{task_key}'.",
                    task_key=task_key,
                )
            TaskCRUD.update_task(db, parent.id, status=TaskStatus.DONE.value)
        finally:
            db.close()

    async def start_from_store(self, task_key: str) -> list[str]:
        """Backwards-compatible alias for `start_task`."""
        return await self.start_task(task_key=task_key)


__all__ = ["TaskExecutor"]
