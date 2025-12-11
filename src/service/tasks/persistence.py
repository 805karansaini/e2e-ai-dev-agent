from __future__ import annotations

import asyncio
from pathlib import Path

from src.service.database_handler import SQLiteTaskStore
from src.service.jira import JiraContext

from .models import TaskPayload


class TaskPersistence:
    """Persist Jira context and task metadata to the task store."""

    def __init__(self, db_path: Path, attachments_dir: Path) -> None:
        self._store = SQLiteTaskStore(db_path, attachments_dir)

    @property
    def db_path(self) -> Path:
        return self._store.db_path

    async def persist(self, context: JiraContext, payload: TaskPayload) -> None:
        await asyncio.to_thread(
            self._store.persist_context,
            context.task,
            context.subtask_prompts,
            context.attachments,
            context.detailed_description,
            payload.repo_url,
            payload.base_branch,
        )


__all__ = ["TaskPersistence"]
