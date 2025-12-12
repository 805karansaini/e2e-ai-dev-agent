"""Database Task CRUD endpoints."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.schemas import (
    CreateSubTask,
    CreateTask,
    SubTaskUpdate,
    Success,
    TaskBase,
    TaskList,
    TaskResponse,
    TaskSearchRequest,
    TaskUpdate,
    success,
)
from src.service.database_handler.config import get_db_session
from src.service.database_handler.crud import TaskCRUD
from src.service.database_handler.models.task import TaskStatus, TaskType

router = APIRouter(prefix="/db/tasks", tags=["database-tasks"])


def _raise_unique_conflict() -> None:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Task with given task_id or sub_task_id already exists",
    )


def get_db() -> Session:
    """Dependency to get database session."""
    db = get_db_session()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "",
    response_model=Success[TaskResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_task(
    task_data: CreateTask, db: Session = Depends(get_db)
) -> Success[TaskResponse]:
    """Create a new task."""
    try:
        # Convert attachment_path to dict list for JSON serialization
        attachment_path_dict = None
        if task_data.attachment_path:
            attachment_path_dict = [
                {"filename": ap.filename, "path": ap.path}
                for ap in task_data.attachment_path
            ]

        task = TaskCRUD.create_task(
            db=db,
            task_id=task_data.task_id,
            task_type=TaskType.TASK.value,  # Already a string
            description=task_data.description,
            repo_url=task_data.repo_url,
            base_branch=task_data.base_branch,
            attachment_path=attachment_path_dict,
            status=task_data.status,  # Already a string
            prompt=task_data.prompt,
            summary=task_data.summary,
            agent_summary=task_data.agent_summary,
            additional_json=task_data.additional_json,
        )

        return success(
            TaskResponse.model_validate(task), status_code=status.HTTP_201_CREATED
        )

    except HTTPException:
        # Preserve intended client errors (e.g., conflicts/validation).
        raise
    except IntegrityError:
        _raise_unique_conflict()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create task: {str(e)}",
        )


@router.post(
    "create-sub-task",
    response_model=Success[TaskResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_sub_task(
    sub_task_data: CreateSubTask, db: Session = Depends(get_db)
) -> Success[TaskResponse]:
    """Create a new task."""
    try:
        # Convert attachment_path to dict list for JSON serialization
        attachment_path_dict = None
        if sub_task_data.attachment_path:
            attachment_path_dict = [
                {"filename": ap.filename, "path": ap.path}
                for ap in sub_task_data.attachment_path
            ]

        task = TaskCRUD.create_task(
            db=db,
            task_id=sub_task_data.task_id,
            sub_task_id=sub_task_data.sub_task_id,
            task_type=TaskType.SUBTASK.value,  # Already a string
            description=sub_task_data.description,
            repo_url=sub_task_data.repo_url,
            base_branch=sub_task_data.base_branch,
            attachment_path=attachment_path_dict,
            status=sub_task_data.status,  # Already a string
            prompt=sub_task_data.prompt,
            summary=sub_task_data.summary,
            agent_summary=sub_task_data.agent_summary,
            additional_json=sub_task_data.additional_json,
        )

        return success(
            TaskResponse.model_validate(task), status_code=status.HTTP_201_CREATED
        )

    except HTTPException:
        # Preserve intended client errors (e.g., conflicts/validation).
        raise
    except IntegrityError:
        _raise_unique_conflict()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create task: {str(e)}",
        )


@router.get(
    "/{task_id}",
    response_model=Success[TaskResponse],
)
def get_task(task_id: str, db: Session = Depends(get_db)) -> Success[TaskResponse]:
    """Get a task by task_id."""
    task = TaskCRUD.get_task_by_task_id(db, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with task_id '{task_id}' not found",
        )

    return success(TaskResponse.model_validate(task))


@router.get(
    "/sub-task/{sub_task_id}",
    response_model=Success[TaskResponse],
)
def get_sub_task(
    sub_task_id: str, db: Session = Depends(get_db)
) -> Success[TaskResponse]:
    """Get a task by task_id."""
    sub_task = TaskCRUD.get_sub_task_by_sub_task_id(db, sub_task_id)
    if not sub_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sub task with sub_task_id '{sub_task_id}' not found",
        )
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
    db: Session = Depends(get_db),
) -> Success[TaskList]:
    """List tasks with optional filters and pagination."""
    try:
        if any([status_filter, task_type_filter, query]):
            # Use search function
            tasks = TaskCRUD.search_tasks(
                db=db,
                query=query,
                status=status_filter,
                task_type=task_type_filter,
                skip=skip,
                limit=limit,
            )
            # For search, we need to get total count separately
            from src.service.database_handler.models.task import Task

            total_query = db.query(Task)
            if query:
                from sqlalchemy import or_

                search_filter = or_(
                    Task.description.ilike(f"%{query}%"),
                    Task.summary.ilike(f"%{query}%"),
                    Task.prompt.ilike(f"%{query}%"),
                )
                total_query = total_query.filter(search_filter)
            if status_filter:
                total_query = total_query.filter(Task.status == status_filter)
            if task_type_filter:
                total_query = total_query.filter(Task.task_type == task_type_filter)
            total = total_query.count()
        else:
            # Use regular list function
            tasks = TaskCRUD.get_all_tasks(db=db, skip=skip, limit=limit)
            from src.service.database_handler.models.task import Task

            total = db.query(Task).count()

        task_responses = [TaskResponse.model_validate(task) for task in tasks]

        return success(
            TaskList(tasks=task_responses, total=total, skip=skip, limit=limit)
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tasks: {str(e)}",
        )


@router.put(
    "/{task_id}",
    response_model=Success[TaskResponse],
)
def update_task(
    task_id: str, task_update: TaskUpdate, db: Session = Depends(get_db)
) -> Success[TaskResponse]:
    """Update a task by task_id."""
    # Get the task by task_id first to find the primary key
    task = TaskCRUD.get_task_by_task_id(db, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with task_id '{task_id}' not found",
        )

    try:
        # Prepare update data, excluding None values
        update_data = task_update.model_dump(exclude_unset=True)

        # Convert attachment_path to dict list for JSON serialization if present
        if (
            "attachment_path" in update_data
            and update_data["attachment_path"] is not None
        ):
            update_data["attachment_path"] = [
                {"filename": ap.filename, "path": ap.path}
                for ap in update_data["attachment_path"]
            ]

        # Update the task using the primary key
        updated_task = TaskCRUD.update_task(db, task.id, **update_data)
        if not updated_task:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update task",
            )

        return success(TaskResponse.model_validate(updated_task))

    except HTTPException:
        raise
    except IntegrityError:
        _raise_unique_conflict()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update task: {str(e)}",
        )


@router.put(
    "/sub-task/{sub_task_id}",
    response_model=Success[TaskResponse],
)
def update_task(
    sub_task_id: str, task_update: SubTaskUpdate, db: Session = Depends(get_db)
) -> Success[TaskResponse]:
    """Update a task by task_id."""
    # Get the task by task_id first to find the primary key
    task = TaskCRUD.get_sub_task_by_sub_task_id(db, sub_task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sub task with sub_task_id '{sub_task_id}' not found",
        )

    try:
        # Prepare update data, excluding None values
        update_data = task_update.model_dump(exclude_unset=True)

        # Convert attachment_path to dict list for JSON serialization if present
        if (
            "attachment_path" in update_data
            and update_data["attachment_path"] is not None
        ):
            update_data["attachment_path"] = [
                {"filename": ap.filename, "path": ap.path}
                for ap in update_data["attachment_path"]
            ]

        # Update the task using the primary key
        updated_task = TaskCRUD.update_task(db, task.id, **update_data)
        if not updated_task:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update task",
            )

        return success(TaskResponse.model_validate(updated_task))

    except HTTPException:
        raise
    except IntegrityError:
        _raise_unique_conflict()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update task: {str(e)}",
        )


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_task(task_id: str, db: Session = Depends(get_db)):
    """Delete a task by task_id."""
    # Get the task by task_id first to find the primary key
    task = TaskCRUD.get_task_by_task_id(db, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with task_id '{task_id}' not found",
        )

    try:
        success_flag = TaskCRUD.delete_task(db, task.id)
        if not success_flag:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete task",
            )

        return None  # 204 No Content

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete task: {str(e)}",
        )


@router.delete(
    "/sub-task/{sub_task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_sub_task(sub_task_id: str, db: Session = Depends(get_db)):
    """Delete a task by task_id."""
    # Get the task by task_id first to find the primary key
    task = TaskCRUD.get_sub_task_by_sub_task_id(db, sub_task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sub task with sub_task_id '{sub_task_id}' not found",
        )

    try:
        success_flag = TaskCRUD.delete_task(db, task.id)
        if not success_flag:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete task",
            )

        return None  # 204 No Content

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete task: {str(e)}",
        )
