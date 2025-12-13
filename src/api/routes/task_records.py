"""Task record CRUD endpoints (database-backed)."""

from __future__ import annotations

import logging
from typing import Optional

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
    JiraImportServiceError,
    JiraIssueNotFoundError,
    TaskConflictError,
    TaskNotFoundError,
    TaskService,
    TaskServiceError,
)
from src.api.services import (
    import_task_from_jira as import_task_from_jira_service,
)
from src.service.database_handler.config import get_db_session
from src.service.database_handler.models.task import TaskStatus, TaskType

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
        result = await import_task_from_jira_service(request, task_service=service)
        return success(
            TaskResponse.model_validate(result.task),
            status_code=(
                status.HTTP_200_OK if result.existed_before else status.HTTP_201_CREATED
            ),
        )
    except HTTPException:
        raise
    except JiraIssueNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except TaskServiceError as exc:
        _raise_http_error(exc)
    except JiraImportServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import task from Jira: {str(exc)}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import task from Jira: {str(exc)}",
        ) from exc

