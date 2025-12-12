"""API route modules."""

from src.api.routes.health import router as health_router
from src.api.routes.task_execution import router as task_execution_router
from src.api.routes.task_records import router as task_records_router

__all__ = ["health_router", "task_execution_router", "task_records_router"]
