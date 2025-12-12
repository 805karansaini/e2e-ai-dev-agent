"""API route modules."""

from src.api.routes.db_tasks import router as db_tasks_router
from src.api.routes.health import router as health_router
from src.api.routes.tasks import router as tasks_router

__all__ = ["health_router", "tasks_router", "db_tasks_router"]
