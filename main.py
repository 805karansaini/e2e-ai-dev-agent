"""Entrypoint for running the FastAPI server with uvicorn."""

from __future__ import annotations

import os
import sys

import uvicorn
from loguru import logger

# Ensure src is importable when running as a script
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.core.config import settings  # noqa: E402
from src.core.logging_config import setup_logging  # noqa: E402


def run_server() -> None:
    """Run uvicorn with the configured application."""

    setup_logging()

    config = uvicorn.Config(
        "src.api.app:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=False,
        log_level=settings.LOG_LEVEL.lower(),
    )
    server = uvicorn.Server(config)
    server.run()


def main() -> None:
    """Entrypoint when executed as a script."""

    try:
        run_server()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user.")


if __name__ == "__main__":
    main()
