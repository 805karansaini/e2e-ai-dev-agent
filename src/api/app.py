"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from src.api.middleware import install_logging_middleware
from src.api.routes import health_router, task_execution_router, task_records_router
from src.service.database_handler import create_tables
from src.service.tasks import task_runner


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Start and stop shared services during the application lifespan."""

    # Ensure database schema exists regardless of how the ASGI app is started.
    create_tables()

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
    app.include_router(task_execution_router)
    app.include_router(task_records_router)

    logger.info("FastAPI application created.")
    return app


# Default application instance
app = create_app()
