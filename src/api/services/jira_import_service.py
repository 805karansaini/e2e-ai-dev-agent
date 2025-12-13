"""Jira import business logic used by API routes.

The Jira context builder + persistence layer (`src.service.tasks.build_and_persist_context`)
already fetches Jira issues/subtasks, downloads attachments, and upserts parent/subtask
rows in the database.

This module contains *API-facing* post-processing that makes the import more useful for
the DB-backed task API:
- split downloaded attachments into parent vs subtask buckets
- enrich `additional_json` with structured Jira metadata (full payload + convenient fields)
- ensure subtasks have attachment + metadata fields updated (best-effort, resilient)

Importantly, this module is FastAPI-agnostic so it can be reused by other callers.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Mapping

from src.api.schemas import (
    CreateSubTask,
    ImportJiraTaskRequest,
    SubTaskUpdate,
    TaskUpdate,
)
from src.api.services.task_service import (
    TaskNotFoundError,
    TaskService,
    TaskServiceError,
)
from src.service.database_handler.models.task import Task, TaskStatus
from src.service.jira import JiraTask
from src.service.jira.import_utils import (
    jira_metadata,
    split_downloaded_attachment_paths,
)
from src.service.tasks import TaskPayload, build_and_persist_context

logger = logging.getLogger(__name__)


class JiraImportServiceError(Exception):
    """Base exception for Jira import failures (service-layer)."""


class JiraIssueNotFoundError(JiraImportServiceError):
    """Raised when a Jira issue key doesn't exist."""


@dataclass(frozen=True, slots=True)
class JiraImportResult:
    """Result of importing from Jira into the task DB."""

    task: Task
    existed_before: bool


async def import_task_from_jira(
    request: ImportJiraTaskRequest,
    *,
    task_service: TaskService,
) -> JiraImportResult:
    """Import a Jira task/subtasks into the DB and enrich stored metadata.

    This function is idempotent: importing the same Jira issue key again will update
    the DB rows in place rather than duplicating them.
    """

    existed_before = True
    try:
        task_service.get_task(request.jira_task_id)
    except TaskNotFoundError:
        existed_before = False

    payload = TaskPayload(
        task_id=request.jira_task_id,
        repo_url=request.repo_url,
        base_branch=request.branch,
    )

    try:
        context = await build_and_persist_context(payload)
    except RuntimeError as exc:
        # Jira context builder raises RuntimeError when Jira issue doesn't exist or
        # Jira is not configured. Provide a typed error for routes/other callers.
        if "was not found" in str(exc):
            raise JiraIssueNotFoundError(
                f"Jira task '{request.jira_task_id}' not found."
            ) from exc
        raise JiraImportServiceError(str(exc)) from exc

    jira_task = context.task

    subtask_keys = {st.key for st in jira_task.subtasks if st.key}
    task_attachments, subtask_attachments = split_downloaded_attachment_paths(
        context.attachments, parent_key=jira_task.key, subtask_keys=subtask_keys
    )

    # The call above already persisted parent + subtasks via TaskPersistence.
    # Here we update metadata/attachments (idempotent) and return the parent.
    task = task_service.get_task(jira_task.key)
    task = task_service.update_task(
        jira_task.key,
        TaskUpdate(
            summary=jira_task.summary or jira_task.key,
            repo_url=request.repo_url,
            base_branch=request.branch,
            attachment_path=task_attachments or None,
            additional_json=jira_metadata(jira_task),
        ),
    )

    _best_effort_update_subtasks(
        jira_task=jira_task,
        subtask_attachments=subtask_attachments,
        request=request,
        task_service=task_service,
    )

    return JiraImportResult(task=task, existed_before=existed_before)


def _best_effort_update_subtasks(
    *,
    jira_task: JiraTask,
    subtask_attachments: Mapping[str, list[dict[str, str]]],
    request: ImportJiraTaskRequest,
    task_service: TaskService,
) -> None:
    """Update/insert subtask metadata and attachments without failing the import."""

    for subtask in jira_task.subtasks:
        if not subtask.key:
            continue
        # Never treat the parent key as a subtask identifier.
        if subtask.key == jira_task.key:
            continue

        try:
            task_service.update_sub_task(
                subtask.key,
                SubTaskUpdate(
                    repo_url=request.repo_url,
                    base_branch=request.branch,
                    attachment_path=subtask_attachments.get(subtask.key) or None,
                    additional_json=jira_metadata(subtask),
                ),
            )
        except TaskNotFoundError:
            # If persistence didn't create a row for some reason, create it now.
            subtask_summary = subtask.summary or subtask.key
            subtask_description = subtask.description or ""
            try:
                task_service.create_sub_task(
                    CreateSubTask(
                        task_id=jira_task.key,
                        sub_task_id=subtask.key,
                        summary=subtask_summary,
                        description=subtask_description,
                        repo_url=request.repo_url,
                        base_branch=request.branch,
                        attachment_path=subtask_attachments.get(subtask.key) or None,
                        status=TaskStatus.PENDING.value,
                        additional_json=jira_metadata(subtask),
                    )
                )
            except TaskServiceError as exc:
                logger.warning("Failed to create subtask %s: %s", subtask.key, exc)
        except TaskServiceError as exc:
            # Keep importing other subtasks; return the main task either way.
            logger.warning("Failed to update subtask %s: %s", subtask.key, exc)
