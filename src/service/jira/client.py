from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Dict, List, Optional

import aiohttp
from pydantic import BaseModel, ConfigDict

from src.core.config import settings

from .models import JiraAttachment, JiraSubtask, JiraTask
from .parsers import (
    parse_jira_attachment,
    parse_jira_comment,
    parse_jira_task,
)


class JiraConfig(BaseModel):
    """Configuration for Jira client."""

    model_config = ConfigDict(frozen=True)

    base_url: str
    email: str
    api_token: str
    project_key: str
    verify_ssl: bool = True

    @classmethod
    def from_env(cls) -> "JiraConfig":
        """Construct configuration from application settings."""
        return cls(
            base_url=settings.JIRA_BASE_URL,
            email=settings.JIRA_EMAIL,
            api_token=settings.JIRA_API_TOKEN,
            project_key=settings.JIRA_PROJECT_KEY,
            verify_ssl=settings.JIRA_VERIFY_SSL,
        )


class JiraClient:
    """Async Jira client built around aiohttp."""

    def __init__(
        self,
        config: JiraConfig,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> None:
        self.config = config
        self._session = session
        self._owns_session = session is None

    async def __aenter__(self) -> "JiraClient":
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - cleanup
        if self._owns_session and self._session:
            await self._session.close()

    @property
    def session(self) -> aiohttp.ClientSession:
        if not self._session:
            raise RuntimeError("Client session is not initialized")
        return self._session

    async def _ensure_session(self) -> None:
        if self._session:
            return
        connector = aiohttp.TCPConnector(ssl=self.config.verify_ssl)
        self._session = aiohttp.ClientSession(
            auth=aiohttp.BasicAuth(self.config.email, self.config.api_token),
            connector=connector,
        )

    async def fetch_issues(
        self,
        jql: str,
        start_at: int = 0,
        max_results: int = 50,
    ) -> Dict:
        """Fetch a page of issues using a JQL query."""

        await self._ensure_session()
        url = f"{self.config.base_url}/rest/api/3/search"
        params = {
            "jql": jql,
            "fields": "*all",
            "startAt": start_at,
            "maxResults": max_results,
        }
        async with self.session.get(url, params=params) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def fetch_all_issues(self) -> List[Dict]:
        """Fetch all issues for the configured project, handling pagination."""
        jql = f'project = "{self.config.project_key}" ORDER BY created DESC'
        all_issues: List[Dict] = []
        start_at = 0
        max_results = 50

        while True:
            data = await self.fetch_issues(
                jql, start_at=start_at, max_results=max_results
            )
            issues = data.get("issues", [])
            if not issues:
                break

            all_issues.extend(issues)
            start_at += len(issues)

            total = data.get("total", start_at)
            if start_at >= total:
                break

        return all_issues

    async def fetch_issue_with_subtasks(self, issue_key: str) -> Optional[JiraTask]:
        """Fetch a specific issue and all its subtasks."""
        await self._ensure_session()
        url = f"{self.config.base_url}/rest/api/3/issue/{issue_key}"
        params = {
            "fields": "*all",
            "expand": "renderedFields",
        }

        async with self.session.get(url, params=params) as resp:
            if resp.status == 404:
                return None
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"Error fetching {issue_key}: {resp.status} {text}")
            issue_data = await resp.json()
            return parse_jira_task(issue_data)

    async def fetch_multiple_issues_with_subtasks(
        self, issue_keys: List[str]
    ) -> List[JiraTask]:
        """Fetch multiple issues and their subtasks concurrently."""
        await self._ensure_session()
        tasks = [self.fetch_issue_with_subtasks(key) for key in issue_keys]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_tasks: List[JiraTask] = []
        for issue_key, result in zip(issue_keys, results):
            if isinstance(result, Exception):
                # Log and continue; upstream caller can decide what to do.
                print(f"Error fetching issue {issue_key}: {result}")
            elif result is not None:
                valid_tasks.append(result)
        return valid_tasks

    async def download_attachments_for_task(
        self, task: JiraTask, base_dir: Path
    ) -> List[Path]:
        """
        Download attachments for a Jira task and its subtasks.

        Files are stored under:
            base_dir/<ISSUE_KEY>/...
        and for subtasks:
            base_dir/<ISSUE_KEY>/<SUBTASK_KEY>/...
        """
        await self._ensure_session()
        saved_paths: List[Path] = []

        def safe_filename(name: Optional[str], fallback: str) -> str:
            if not name:
                return fallback
            return Path(name).name or fallback

        async def download_one(url: str, dest: Path) -> Optional[Path]:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    print(f"Failed to download {url}: HTTP {resp.status}")
                    return None
                data = await resp.read()
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                return dest

        issue_dir = base_dir / task.key

        for attachment in task.attachments:
            if not attachment.content:
                continue
            filename = safe_filename(attachment.filename, attachment.id or "attachment")
            dest = issue_dir / filename
            if dest.exists():
                saved_paths.append(dest)
                continue
            saved = await download_one(attachment.content, dest)
            if saved:
                saved_paths.append(saved)

        for subtask in task.subtasks:
            if not subtask.attachments:
                continue
            subtask_dir = issue_dir / subtask.key
            for attachment in subtask.attachments:
                if not attachment.content:
                    continue
                filename = safe_filename(
                    attachment.filename, attachment.id or "attachment"
                )
                dest = subtask_dir / filename
                if dest.exists():
                    saved_paths.append(dest)
                    continue
                saved = await download_one(attachment.content, dest)
                if saved:
                    saved_paths.append(saved)

        return saved_paths


__all__ = ["JiraAttachment", "JiraClient", "JiraConfig", "JiraSubtask", "JiraTask"]
