"""Jira-specific import helpers.

These helpers are intentionally Jira-focused and framework-agnostic:
- attachment path bucketing (parent vs subtask)
- metadata extraction for storage/logging
"""

from __future__ import annotations

from pathlib import Path
from typing import AbstractSet, Any, Iterable

from .models import JiraSubtask, JiraTask


def split_downloaded_attachment_paths(
    paths: Iterable[Path] | None,
    *,
    parent_key: str,
    subtask_keys: AbstractSet[str],
) -> tuple[list[dict[str, str]], dict[str, list[dict[str, str]]]]:
    """Split downloaded attachment paths into task vs subtask buckets.

    The download path convention is:
      <attachments_dir>/<PARENT_KEY>/<filename>
    or:
      <attachments_dir>/<PARENT_KEY>/<SUBTASK_KEY>/<filename>
    """

    task_attachments: list[dict[str, str]] = []
    subtask_attachments: dict[str, list[dict[str, str]]] = {}

    for p in paths or []:
        path = Path(p)
        record = {"filename": path.name, "path": str(path)}

        parts = path.parts
        try:
            idx = parts.index(parent_key)
        except ValueError:
            # Unexpected layout; treat it as a parent attachment so we don't lose it.
            task_attachments.append(record)
            continue

        if idx + 1 < len(parts) and parts[idx + 1] in subtask_keys:
            subtask_key = parts[idx + 1]
            subtask_attachments.setdefault(subtask_key, []).append(record)
        else:
            task_attachments.append(record)

    return task_attachments, subtask_attachments


def jira_metadata(issue: JiraTask | JiraSubtask) -> dict[str, Any]:
    """Best-effort Jira metadata (json-serializable)."""

    status = issue.status.model_dump(mode="json") if issue.status else None
    assignee = issue.assignee.model_dump(mode="json") if issue.assignee else None
    reporter = issue.reporter.model_dump(mode="json") if issue.reporter else None
    priority = issue.priority.model_dump(mode="json") if issue.priority else None

    created = issue.created.isoformat() if getattr(issue, "created", None) else None
    updated = issue.updated.isoformat() if getattr(issue, "updated", None) else None

    return {
        # Convenient flat keys (easy to query / filter)
        "jira_id": getattr(issue, "id", None),
        "jira_key": getattr(issue, "key", None),
        "jira_status": status,
        "jira_assignee": assignee,
        "jira_reporter": reporter,
        "jira_priority": priority,
        "jira_labels": getattr(issue, "labels", []) or [],
        "jira_created": created,
        "jira_updated": updated,
        # Full payload for completeness/debugging
        "jira": issue.model_dump(mode="json"),
    }


__all__ = ["jira_metadata", "split_downloaded_attachment_paths"]
