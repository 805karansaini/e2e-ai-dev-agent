from __future__ import annotations

import logging
import sys

from loguru import logger

from src.core.config import settings

_HEALTH_PATHS = {"/health/liveness", "/health/readiness"}

LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level:<8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)


class SuppressHealthCheckAccessLogs(logging.Filter):
    """Filter to suppress access logs for healthy liveness/readiness checks."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
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
        return path not in _HEALTH_PATHS


class InterceptHandler(logging.Handler):
    """Route stdlib logging records through loguru for unified output."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging() -> None:
    """Configure loguru with colorful formatting and stdlib interception."""

    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.LOG_LEVEL.upper(),
        format=LOG_FORMAT,
        colorize=True,
        enqueue=True,
        backtrace=False,
        diagnose=False,
    )

    intercept = InterceptHandler()
    logging.basicConfig(handlers=[intercept], level=0, force=True)

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = [intercept]
        uvicorn_logger.propagate = False

    logging.getLogger("uvicorn.access").addFilter(SuppressHealthCheckAccessLogs())


__all__ = ["setup_logging", "InterceptHandler", "SuppressHealthCheckAccessLogs"]
