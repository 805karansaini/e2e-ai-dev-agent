"""Schemas for health endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class LivenessStatus(BaseModel):
    """Response payload for liveness check."""

    probe: Literal["liveness"] = "liveness"
    status: Literal["ok"] = "ok"
    message: str = Field(
        "service is running",
        description="Human-friendly message describing liveness state",
    )


class ReadinessStatus(BaseModel):
    """Response payload for readiness check."""

    probe: Literal["readiness"] = "readiness"
    status: Literal["ready", "degraded"] = "ready"
    cline_cli_available: bool
    task_worker_running: bool
    queued_tasks: int = 0
    details: str | None = Field(
        None,
        description="Optional detail when readiness is degraded.",
    )
