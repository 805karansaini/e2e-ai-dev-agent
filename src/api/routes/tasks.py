"""Task endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from src.api.schemas import (
    SubtaskPromptSchema,
    Success,
    TaskAutoResponse,
    TaskCreateRequest,
    TaskPlanResponse,
    TaskStartResponse,
    success,
)
from src.service.tasks import TaskPayload, task_executor, task_orchestrator

router = APIRouter(tags=["tasks"])


def _ensure_cli_available() -> None:
    if not task_executor.cli_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CLINE CLI binary is not available on this host.",
        )


def _map_subtasks(subtasks: list) -> list[SubtaskPromptSchema]:
    return [
        SubtaskPromptSchema(
            subtask_key=sub.subtask_key,
            summary=sub.summary,
            description=sub.description,
            prompt=sub.prompt,
        )
        for sub in subtasks
    ]


@router.post(
    "/tasks/orchestrator",
    response_model=Success[TaskPlanResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Task Orchestrator",
)
async def orchestrate_task(body: TaskCreateRequest) -> Success[TaskPlanResponse]:
    """Generate prompts and a full execution plan for a task."""

    _ensure_cli_available()

    payload = TaskPayload(
        task_id=body.task_id,
        repo_url=body.repo_url,
        base_branch=body.base_branch,
    )

    try:
        result = await task_orchestrator.orchestrate(payload)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    response = TaskPlanResponse(
        task_id=payload.task_id,
        repo_url=payload.repo_url,
        base_branch=payload.base_branch,
        orchestration_prompt=result.orchestration_prompt,
        simple_prompt=result.simple_prompt,
        subtask_prompts=_map_subtasks(result.subtask_prompts),
    )
    return success(response, status_code=status.HTTP_202_ACCEPTED)


@router.post("/tasks", include_in_schema=False)
async def orchestrate_task_legacy(body: TaskCreateRequest) -> Success[TaskPlanResponse]:
    """Backward-compatible entrypoint that maps to Task Orchestrator."""

    return await orchestrate_task(body)


@router.post(
    "/tasks/start",
    response_model=Success[TaskStartResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Task Starter",
)
async def start_task(body: TaskCreateRequest) -> Success[TaskStartResponse]:
    """Start execution using stored prompts for the task and its subtasks."""

    _ensure_cli_available()

    try:
        started = await task_executor.start_from_store(body.task_id)
    except RuntimeError as exc:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if "No stored prompts" in str(exc)
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    response = TaskStartResponse(task_id=body.task_id, started_subtasks=started)
    return success(response, status_code=status.HTTP_202_ACCEPTED)


@router.post(
    "/tasks/auto",
    response_model=Success[TaskAutoResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Complete Auto Dev",
)
async def auto_dev_task(body: TaskCreateRequest) -> Success[TaskAutoResponse]:
    """Orchestrate and start execution in a single request."""

    _ensure_cli_available()

    payload = TaskPayload(
        task_id=body.task_id,
        repo_url=body.repo_url,
        base_branch=body.base_branch,
    )

    try:
        orchestration_result = await task_orchestrator.orchestrate(payload)
        started = await task_executor.start_from_store(payload.task_id)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    response = TaskAutoResponse(
        task_id=payload.task_id,
        orchestration_prompt=orchestration_result.orchestration_prompt,
        started_subtasks=started,
    )
    return success(response, status_code=status.HTTP_202_ACCEPTED)
