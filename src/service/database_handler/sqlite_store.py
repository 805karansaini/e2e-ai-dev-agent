from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List

from src.service.jira import JiraTask
from src.service.jira.prompt_models import SubtaskPrompt


class SQLiteTaskStore:
    """SQLite-backed persistence layer for Jira tasks and subtasks."""

    def __init__(self, db_path: Path, attachments_base: Path) -> None:
        self._db_path = Path(db_path)
        self._attachments_base = Path(attachments_base)

    @property
    def db_path(self) -> Path:
        return self._db_path

    def persist_context(
        self,
        task: JiraTask,
        subtask_prompts: List[SubtaskPrompt],
        attachments: List[Path],
        detailed_description: str,
        repo_url: str,
        base_branch: str,
    ) -> None:
        """Insert or update task context in SQLite."""

        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        try:
            self._ensure_schema(conn)
            self._upsert_task(conn, task, detailed_description, repo_url, base_branch)
            self._upsert_subtasks(conn, task, subtask_prompts)
            self._upsert_attachments(conn, task, attachments)
            conn.commit()
        finally:
            conn.close()

    def _ensure_schema(self, conn: sqlite3.Connection) -> None:
        """Create tables if they do not yet exist."""

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                task_key TEXT PRIMARY KEY,
                summary TEXT,
                description TEXT,
                status TEXT,
                priority TEXT,
                assignee TEXT,
                reporter TEXT,
                labels TEXT,
                detailed_description TEXT,
                repo_url TEXT,
                base_branch TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS subtasks (
                task_key TEXT,
                subtask_key TEXT,
                summary TEXT,
                description TEXT,
                prompt TEXT,
                PRIMARY KEY (task_key, subtask_key),
                FOREIGN KEY (task_key) REFERENCES tasks(task_key)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS attachments (
                task_key TEXT,
                issue_key TEXT,
                subtask_key TEXT,
                path TEXT,
                PRIMARY KEY (task_key, issue_key, subtask_key, path),
                FOREIGN KEY (task_key) REFERENCES tasks(task_key)
            )
            """
        )

    def _upsert_task(
        self,
        conn: sqlite3.Connection,
        task: JiraTask,
        detailed_description: str,
        repo_url: str,
        base_branch: str,
    ) -> None:
        """Insert or update the parent task record."""

        conn.execute(
            """
            INSERT OR REPLACE INTO tasks (
                task_key, summary, description, status, priority, assignee,
                reporter, labels, detailed_description, repo_url, base_branch
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task.key,
                task.summary,
                task.description,
                task.status.name if task.status else None,
                task.priority.name if task.priority else None,
                task.assignee.display_name if task.assignee else None,
                task.reporter.display_name if task.reporter else None,
                ",".join(task.labels) if task.labels else None,
                detailed_description,
                repo_url,
                base_branch,
            ),
        )

    def _upsert_subtasks(
        self,
        conn: sqlite3.Connection,
        task: JiraTask,
        subtask_prompts: List[SubtaskPrompt],
    ) -> None:
        """Insert or update related subtasks."""

        for subtask_prompt in subtask_prompts:
            conn.execute(
                """
                INSERT OR REPLACE INTO subtasks (
                    task_key, subtask_key, summary, description, prompt
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    task.key,
                    subtask_prompt.key,
                    subtask_prompt.summary,
                    subtask_prompt.description,
                    subtask_prompt.prompt,
                ),
            )

    def _upsert_attachments(
        self,
        conn: sqlite3.Connection,
        task: JiraTask,
        attachments: List[Path],
    ) -> None:
        """Insert or update attachment metadata."""

        for path in attachments:
            try:
                relative = path.relative_to(self._attachments_base)
            except ValueError:
                relative = path.name

            parts = Path(relative).parts
            issue_key = parts[0] if parts else task.key
            subtask_key = parts[1] if len(parts) > 1 else None

            conn.execute(
                """
                INSERT OR REPLACE INTO attachments (
                    task_key, issue_key, subtask_key, path
                ) VALUES (?, ?, ?, ?)
                """,
                (task.key, issue_key, subtask_key, str(path)),
            )
