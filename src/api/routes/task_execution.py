"""Task orchestration and execution endpoints."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, status
from loguru import logger

from src.api.schemas import (
    SubtaskPromptSchema,
    Success,
    TaskAutoResponse,
    TaskCreateRequest,
    TaskPlanResponse,
    TaskStartResponse,
    success,
)
from src.service.tasks import (
    TaskPayload,
    task_executor,
    task_orchestrator,
)

router = APIRouter(tags=["tasks"])


def _ensure_cli_available() -> None:
    if not task_executor.cli_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CLINE CLI binary is not available on this host.",
        )


def _payload_from_request(body: TaskCreateRequest) -> TaskPayload:
    """Create a validated task payload from the request body."""
    return TaskPayload(**body.model_dump())


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


def _http_exception_from_runtime(exc: RuntimeError) -> HTTPException:
    """Translate domain errors into appropriate HTTP responses."""
    message = str(exc)
    lowered = message.lower()

    if "not found" in lowered:
        status_code = status.HTTP_404_NOT_FOUND
    elif any(term in lowered for term in ("no stored", "malformed", "invalid")):
        status_code = status.HTTP_400_BAD_REQUEST
    elif "not available" in lowered or "unavailable" in lowered:
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    return HTTPException(status_code=status_code, detail=message)


async def _start_execution(payload: TaskPayload) -> list[str]:
    _ensure_cli_available()
    return await task_executor.start_task(
        task_key=payload.task_id,
        repo_url=payload.repo_url,
        base_branch=payload.base_branch,
    )


async def _start_or_error(body: TaskCreateRequest) -> list[str]:
    payload = _payload_from_request(body)
    try:
        return await _start_execution(payload)
    except RuntimeError as exc:
        raise _http_exception_from_runtime(exc) from exc


async def _auto_dev_background(payload: TaskPayload) -> None:
    """Run orchestration + execution start asynchronously."""
    try:
        await task_orchestrator.orchestrate(payload)
        await _start_execution(payload)
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Auto-dev flow failed for task '{task_id}': {error}",
            task_id=payload.task_id,
            error=exc,
        )


@router.post(
    "/tasks/orchestrator",
    response_model=Success[TaskPlanResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Task Orchestrator",
)
async def orchestrate_task(body: TaskCreateRequest) -> Success[TaskPlanResponse]:
    """Generate prompts and a full execution plan for a task."""

    payload = _payload_from_request(body)
    try:
        result = await task_orchestrator.orchestrate(payload)
    except RuntimeError as exc:
        raise _http_exception_from_runtime(exc) from exc

    response = TaskPlanResponse(
        task_id=payload.task_id,
        repo_url=payload.repo_url,
        base_branch=payload.base_branch,
        orchestration_prompt=result.orchestration_prompt,
        simple_prompt=result.simple_prompt,
        subtask_prompts=_map_subtasks(result.subtask_prompts or []),
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
    """Orchestrate and start execution in a single request (background)."""

    _ensure_cli_available()
    payload = _payload_from_request(body)

    # Queue the long-running orchestration + execution start chain.
    asyncio.create_task(
        _auto_dev_background(payload), name=f"auto-dev-{payload.task_id}"
    )

    response = TaskAutoResponse(
        task_id=payload.task_id,
        orchestration_prompt="",
        started_subtasks=[],
    )
    return success(response, status_code=status.HTTP_202_ACCEPTED)
