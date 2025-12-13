"""Task record CRUD endpoints (database-backed)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.api.schemas import (
    CreateSubTask,
    CreateTask,
    ImportJiraTaskRequest,
    SubTaskUpdate,
    Success,
    TaskList,
    TaskResponse,
    TaskUpdate,
    success,
)
from src.api.services import (
    TaskConflictError,
    TaskNotFoundError,
    TaskService,
    TaskServiceError,
)
from src.service.database_handler.config import get_db_session
from src.service.database_handler.models.task import TaskStatus, TaskType
from src.service.tasks import TaskPayload, build_and_persist_context

router = APIRouter(prefix="/db/tasks", tags=["database-tasks"])
logger = logging.getLogger(__name__)


def get_db() -> Session:
    """Dependency to get database session."""
    db = get_db_session()
    try:
        yield db
    finally:
        db.close()


def get_task_service(db: Session = Depends(get_db)) -> TaskService:
    """Provide TaskService for both API handlers and internal callers."""
    return TaskService(db)


def _raise_http_error(exc: TaskServiceError) -> None:
    if isinstance(exc, TaskNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    if isinstance(exc, TaskConflictError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
    ) from exc


@router.post(
    "",
    response_model=Success[TaskResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_task(
    task_data: CreateTask, service: TaskService = Depends(get_task_service)
) -> Success[TaskResponse]:
    """Create a new task."""
    try:
        task = service.create_task(task_data)
    except TaskServiceError as exc:
        _raise_http_error(exc)

    return success(
        TaskResponse.model_validate(task), status_code=status.HTTP_201_CREATED
    )


@router.post(
    "/sub-task",
    response_model=Success[TaskResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_sub_task(
    sub_task_data: CreateSubTask, service: TaskService = Depends(get_task_service)
) -> Success[TaskResponse]:
    """Create a new sub-task."""
    try:
        task = service.create_sub_task(sub_task_data)
    except TaskServiceError as exc:
        _raise_http_error(exc)

    return success(
        TaskResponse.model_validate(task), status_code=status.HTTP_201_CREATED
    )


@router.get(
    "/{task_id}",
    response_model=Success[TaskResponse],
)
def get_task(
    task_id: str, service: TaskService = Depends(get_task_service)
) -> Success[TaskResponse]:
    """Get a task by task_id."""
    try:
        task = service.get_task(task_id)
    except TaskServiceError as exc:
        _raise_http_error(exc)

    return success(TaskResponse.model_validate(task))


@router.get(
    "/sub-task/{sub_task_id}",
    response_model=Success[TaskResponse],
)
def get_sub_task(
    sub_task_id: str, service: TaskService = Depends(get_task_service)
) -> Success[TaskResponse]:
    """Get a task by task_id."""
    try:
        sub_task = service.get_sub_task(sub_task_id)
    except TaskServiceError as exc:
        _raise_http_error(exc)

    return success(TaskResponse.model_validate(sub_task))


@router.get(
    "",
    response_model=Success[TaskList],
)
def list_tasks(
    skip: int = Query(0, ge=0, description="Number of tasks to skip"),
    limit: Optional[int] = Query(
        None, gt=0, le=1000, description="Maximum number of tasks to return"
    ),
    status_filter: Optional[TaskStatus] = Query(
        None, description="Filter by task status"
    ),
    task_type_filter: Optional[TaskType] = Query(
        None, description="Filter by task type"
    ),
    query: Optional[str] = Query(
        None, description="Search query for description, summary, or prompt"
    ),
    service: TaskService = Depends(get_task_service),
) -> Success[TaskList]:
    """List tasks with optional filters and pagination."""
    try:
        tasks, total = service.list_tasks(
            skip=skip,
            limit=limit,
            status_filter=status_filter,
            task_type_filter=task_type_filter,
            query=query,
        )
    except TaskServiceError as exc:
        _raise_http_error(exc)

    task_responses = [TaskResponse.model_validate(task) for task in tasks]

    return success(TaskList(tasks=task_responses, total=total, skip=skip, limit=limit))


@router.put(
    "/{task_id}",
    response_model=Success[TaskResponse],
)
def update_task(
    task_id: str,
    task_update: TaskUpdate,
    service: TaskService = Depends(get_task_service),
) -> Success[TaskResponse]:
    """Update a task by task_id."""
    try:
        updated_task = service.update_task(task_id, task_update)
    except TaskServiceError as exc:
        _raise_http_error(exc)

    return success(TaskResponse.model_validate(updated_task))


@router.put(
    "/sub-task/{sub_task_id}",
    response_model=Success[TaskResponse],
)
def update_sub_task(
    sub_task_id: str,
    task_update: SubTaskUpdate,
    service: TaskService = Depends(get_task_service),
) -> Success[TaskResponse]:
    """Update a task by task_id."""
    try:
        updated_task = service.update_sub_task(sub_task_id, task_update)
    except TaskServiceError as exc:
        _raise_http_error(exc)

    return success(TaskResponse.model_validate(updated_task))


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_task(task_id: str, service: TaskService = Depends(get_task_service)):
    """Delete a task by task_id."""
    try:
        service.delete_task(task_id)
    except TaskServiceError as exc:
        _raise_http_error(exc)

    return None  # 204 No Content


@router.delete(
    "/sub-task/{sub_task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_sub_task(sub_task_id: str, service: TaskService = Depends(get_task_service)):
    """Delete a task by task_id."""
    try:
        service.delete_sub_task(sub_task_id)
    except TaskServiceError as exc:
        _raise_http_error(exc)

    return None  # 204 No Content


@router.post(
    "/import-from-jira",
    response_model=Success[TaskResponse],
    status_code=status.HTTP_201_CREATED,
)
async def import_task_from_jira(
    request: ImportJiraTaskRequest,
    service: TaskService = Depends(get_task_service),
) -> Success[TaskResponse]:
    """Import a task from Jira and insert it into the database."""
    try:
        # Determine whether this task existed prior to import so we can return
        # 201 (created) vs 200 (updated) while keeping the endpoint idempotent.
        existed_before = True
        try:
            service.get_task(request.jira_task_id)
        except TaskNotFoundError:
            existed_before = False

        def _split_attachment_paths(
            paths: list[Path] | None,
            *,
            parent_key: str,
            subtask_keys: set[str],
        ) -> tuple[list[dict[str, str]], dict[str, list[dict[str, str]]]]:
            """Split downloaded attachment paths into task vs subtask buckets."""

            task_attachments: list[dict[str, str]] = []
            subtask_attachments: dict[str, list[dict[str, str]]] = {}

            for p in paths or []:
                path = Path(p)
                record = {"filename": path.name, "path": str(path)}

                # The download path convention is:
                #   <attachments_dir>/<PARENT_KEY>/<filename>
                # or
                #   <attachments_dir>/<PARENT_KEY>/<SUBTASK_KEY>/<filename>
                parts = path.parts
                try:
                    idx = parts.index(parent_key)
                except ValueError:
                    task_attachments.append(record)
                    continue

                if idx + 1 < len(parts) and parts[idx + 1] in subtask_keys:
                    subtask_key = parts[idx + 1]
                    subtask_attachments.setdefault(subtask_key, []).append(record)
                else:
                    task_attachments.append(record)

            return task_attachments, subtask_attachments

        def _jira_metadata(issue: Any) -> dict[str, Any]:
            """Best-effort Jira metadata (json-serializable)."""

            status = issue.status.model_dump(mode="json") if issue.status else None
            assignee = (
                issue.assignee.model_dump(mode="json") if issue.assignee else None
            )
            reporter = (
                issue.reporter.model_dump(mode="json") if issue.reporter else None
            )
            priority = (
                issue.priority.model_dump(mode="json") if issue.priority else None
            )
            return {
                # Backward-ish compatible flat keys (easy to query / filter)
                "jira_id": getattr(issue, "id", None),
                "jira_key": getattr(issue, "key", None),
                "jira_status": status,
                "jira_assignee": assignee,
                "jira_reporter": reporter,
                "jira_priority": priority,
                "jira_labels": getattr(issue, "labels", []) or [],
                "jira_created": issue.created.isoformat() if issue.created else None,
                "jira_updated": issue.updated.isoformat() if issue.updated else None,
                # Full payload for completeness/debugging
                "jira": issue.model_dump(mode="json"),
            }

        payload = TaskPayload(
            task_id=request.jira_task_id,
            repo_url=request.repo_url,
            base_branch=request.branch,
        )
        context = await build_and_persist_context(payload)

        jira_task = context.task
        subtask_keys = {st.key for st in jira_task.subtasks if st.key}
        task_attachments, subtask_attachments = _split_attachment_paths(
            context.attachments, parent_key=jira_task.key, subtask_keys=subtask_keys
        )

        # The call above already persisted parent + subtasks via TaskPersistence.
        # Here we update metadata/attachments (idempotent) and return the parent.
        try:
            task = service.get_task(jira_task.key)
        except TaskServiceError as exc:
            _raise_http_error(exc)

        try:
            task = service.update_task(
                jira_task.key,
                TaskUpdate(
                    summary=jira_task.summary or jira_task.key,
                    repo_url=request.repo_url,
                    base_branch=request.branch,
                    attachment_path=task_attachments or None,
                    additional_json=_jira_metadata(jira_task),
                ),
            )
        except TaskServiceError as exc:
            _raise_http_error(exc)

        for subtask in jira_task.subtasks:
            if not subtask.key:
                continue
            subtask_summary = subtask.summary or subtask.key
            subtask_description = subtask.description or ""
            try:
                service.update_sub_task(
                    subtask.key,
                    SubTaskUpdate(
                        repo_url=request.repo_url,
                        base_branch=request.branch,
                        attachment_path=subtask_attachments.get(subtask.key) or None,
                        additional_json=_jira_metadata(subtask),
                    ),
                )
            except TaskNotFoundError:
                # If persistence didn't create a row for some reason, create it now.
                try:
                    service.create_sub_task(
                        CreateSubTask(
                            task_id=jira_task.key,
                            sub_task_id=subtask.key,
                            summary=subtask_summary,
                            description=subtask_description,
                            repo_url=request.repo_url,
                            base_branch=request.branch,
                            attachment_path=subtask_attachments.get(subtask.key)
                            or None,
                            status=TaskStatus.PENDING.value,
                            additional_json=_jira_metadata(subtask),
                        )
                    )
                except TaskServiceError as exc:
                    logger.warning("Failed to create subtask %s: %s", subtask.key, exc)
            except TaskServiceError as exc:
                # Keep importing other subtasks; return the main task either way.
                logger.warning("Failed to create subtask %s: %s", subtask.key, exc)

        return success(
            TaskResponse.model_validate(task),
            status_code=(
                status.HTTP_200_OK if existed_before else status.HTTP_201_CREATED
            ),
        )
    except HTTPException:
        raise
    except RuntimeError as exc:
        # Jira context builder raises a RuntimeError when the Jira issue doesn't exist.
        if "was not found" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Jira task '{request.jira_task_id}' not found.",
            ) from exc
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import task from Jira: {str(exc)}",
        ) from exc
