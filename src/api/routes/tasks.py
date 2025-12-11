"""Task endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from src.api.schemas import Success, TaskAccepted, TaskCreateRequest, success
from src.service.tasks import TaskPayload, task_runner

router = APIRouter(tags=["tasks"])


@router.post(
    "/tasks",
    response_model=Success[TaskAccepted],
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_task(body: TaskCreateRequest) -> Success[TaskAccepted]:
    """Enqueue and start a new CLINE CLI task."""

    if not task_runner.cli_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CLINE CLI binary is not available on this host.",
        )

    payload = TaskPayload(
        task_id=body.task_id,
        repo_url=body.repo_url,
        base_branch=body.base_branch,
    )

    try:
        await task_runner.enqueue(payload)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    response = TaskAccepted(task_id=body.task_id)
    return success(response, status_code=status.HTTP_202_ACCEPTED)
