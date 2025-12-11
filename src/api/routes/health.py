"""Health and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter, status

from src.api.schemas import LivenessStatus, ReadinessStatus, Success, success
from src.service.tasks import task_runner

router = APIRouter(prefix="/health", tags=["health"])


@router.get(
    "/liveness",
    response_model=Success[LivenessStatus],
    status_code=status.HTTP_200_OK,
)
async def liveness_probe() -> Success[LivenessStatus]:
    """Basic liveness probe."""

    payload = LivenessStatus()
    return success(payload)


@router.get(
    "/readiness",
    response_model=Success[ReadinessStatus],
)
async def readiness_probe() -> Success[ReadinessStatus]:
    """Readiness probe that reflects CLINE CLI and worker health."""

    cli_ok = task_runner.cli_available
    worker_ok = task_runner.is_running
    all_ok = cli_ok and worker_ok

    details: str | None = None
    if not cli_ok:
        details = "CLINE CLI binary is not available in PATH."
    elif not worker_ok:
        details = "Task worker is not running yet."

    payload = ReadinessStatus(
        status="ready" if all_ok else "degraded",
        cline_cli_available=cli_ok,
        task_worker_running=worker_ok,
        queued_tasks=task_runner.queued_tasks,
        details=details,
    )
    http_status = status.HTTP_200_OK if all_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return success(payload, status_code=http_status)
