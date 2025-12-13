"""Task orchestration and execution endpoints."""

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


def _build_payload(body: TaskCreateRequest) -> TaskPayload:
    return TaskPayload(
        task_id=body.task_id,
        repo_url=body.repo_url,
        base_branch=body.base_branch,
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


def _raise_unavailable(exc: RuntimeError) -> None:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
    ) from exc


async def _start_or_error(body: TaskCreateRequest) -> list[str]:
    _ensure_cli_available()
    try:
        return await task_executor.start_task(
            task_key=body.task_id, repo_url=body.repo_url, base_branch=body.base_branch
        )
    except RuntimeError as exc:
        message = str(exc)
        status_code = (
            status.HTTP_404_NOT_FOUND
            if "not found" in message.lower()
            else status.HTTP_400_BAD_REQUEST
            if "no stored" in message.lower() or "malformed" in message.lower()
            else status.HTTP_503_SERVICE_UNAVAILABLE
            if "not available" in message.lower()
            else status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.post(
    "/tasks/orchestrator",
    response_model=Success[TaskPlanResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Task Orchestrator",
)
async def orchestrate_task(body: TaskCreateRequest) -> Success[TaskPlanResponse]:
    """Generate prompts and a full execution plan for a task."""

    payload = _build_payload(body)
    try:
        result = await task_orchestrator.orchestrate(payload)
    except RuntimeError as exc:
        _raise_unavailable(exc)

    response = TaskPlanResponse(
        task_id=payload.task_id,
        repo_url=payload.repo_url,
        base_branch=payload.base_branch,
        orchestration_prompt=result.orchestration_prompt,
        simple_prompt=result.simple_prompt,
        subtask_prompts=_map_subtasks(result.subtask_prompts),
    )
    return success(response, status_code=status.HTTP_202_ACCEPTED)


@router.post(
    "/tasks/start",
    response_model=Success[TaskStartResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Task Starter",
)
async def start_task(body: TaskCreateRequest) -> Success[TaskStartResponse]:
    """Start execution using stored prompts for the task and its subtasks."""

    started = await _start_or_error(body)

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

    payload = _build_payload(body)

    try:
        orchestration_result = await task_orchestrator.orchestrate(payload)
    except RuntimeError as exc:
        _raise_unavailable(exc)

    started = await _start_or_error(body)

    response = TaskAutoResponse(
        task_id=payload.task_id,
        orchestration_prompt=orchestration_result.orchestration_prompt,
        started_subtasks=started,
    )
    return success(response, status_code=status.HTTP_202_ACCEPTED)
