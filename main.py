"""Entrypoint for running the FastAPI server with uvicorn."""

from __future__ import annotations

import logging
import os
import sys

import uvicorn

# Ensure src is importable when running as a script
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.core.config import settings  # noqa: E402


class SuppressHealthCheckAccessLogs(logging.Filter):
    """Filter to suppress access logs for successful health checks."""

    health_paths = {"/health/liveness", "/health/readiness"}

    def filter(self, record: logging.LogRecord) -> bool:
        if record.name != "uvicorn.access":
            return True

        try:
            _, method, raw_path, _, status_code = record.args  # type: ignore[misc]
        except Exception:
            return True

        path = str(raw_path).split("?", 1)[0]
        if method != "GET":
            return True
        if int(status_code) != 200:
            return True
        return path not in self.health_paths


def _configure_logging() -> None:
    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.addFilter(SuppressHealthCheckAccessLogs())


def run_server() -> None:
    """Run uvicorn with the configured application."""

    _configure_logging()

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
        logging.getLogger(__name__).info("Application interrupted by user.")


if __name__ == "__main__":
    main()
