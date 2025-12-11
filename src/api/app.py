"""FastAPI application factory."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.middleware import install_logging_middleware
from src.api.routes import health_router, tasks_router
from src.service.tasks import task_runner

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Start and stop shared services during the application lifespan."""

    await task_runner.start()
    try:
        yield
    finally:
        await task_runner.stop()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""

    app = FastAPI(
        title="CLINE Task API",
        description="Lightweight API for CLINE task orchestration.",
        version="0.1.0",
        lifespan=lifespan,
    )

    install_logging_middleware(app)
    app.include_router(health_router)
    app.include_router(tasks_router)

    logger.info("FastAPI application created.")
    return app


# Default application instance
app = create_app()
