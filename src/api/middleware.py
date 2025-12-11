"""Lightweight request logging and correlation middleware."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from loguru import logger

_HEALTH_PATHS = {"/health/liveness", "/health/readiness"}


def _should_log(path: str) -> bool:
    return path not in _HEALTH_PATHS


def install_logging_middleware(app: FastAPI) -> None:
    """Attach correlation IDs and simple request/response timing logs."""

    @app.middleware("http")
    async def _logging_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID") or uuid4().hex
        request.state.correlation_id = correlation_id  # handy for handlers
        started = time.perf_counter()
        path = request.url.path

        if _should_log(path):
            logger.info(
                "HTTP request start | id={cid} method={method} path={path}",
                cid=correlation_id,
                method=request.method,
                path=path,
            )

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - started) * 1000
            if _should_log(path):
                logger.exception(
                    "HTTP request error | id={cid} method={method} path={path} latency_ms={latency:.2f}",
                    cid=correlation_id,
                    method=request.method,
                    path=path,
                    latency=duration_ms,
                )
            raise

        duration_ms = (time.perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = correlation_id
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

        if _should_log(path):
            logger.info(
                "HTTP response end | id={cid} method={method} path={path} status={status} latency_ms={latency:.2f}",
                cid=correlation_id,
                method=request.method,
                path=path,
                status=response.status_code,
                latency=duration_ms,
            )

        return response
