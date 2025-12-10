from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from .models import (
    JiraAttachment,
    JiraComment,
    JiraIssueType,
    JiraPriority,
    JiraProject,
    JiraStatus,
    JiraSubtask,
    JiraTask,
    JiraUser,
)


def parse_jira_datetime(date_str: Optional[str]) -> Optional[datetime]:
    """Parse Jira datetime string to a datetime object."""
    if not date_str:
        return None
    try:
        # Jira uses ISO format like "2023-12-01T10:30:00.000+0000"
        return datetime.fromisoformat(date_str.replace("+0000", "+00:00"))
    except (ValueError, TypeError):
        return None


def _collect_adf_text(node: Any) -> str:
    """
    Recursively collect text from Atlassian Document Format (ADF) nodes.

    The Jira Cloud REST API returns rich text fields (e.g., description,
    comments) as ADF objects. This helper flattens them into plain text so
    Pydantic string fields validate correctly.
    """
    if isinstance(node, str):
        return node
    if not isinstance(node, dict):
        return ""

    parts: List[str] = []

    if "text" in node and isinstance(node["text"], str):
        parts.append(node["text"])

    for child in node.get("content", []) or []:
        child_text = _collect_adf_text(child)
        if child_text:
            parts.append(child_text)

    block_types = {
        "paragraph",
        "heading",
        "blockquote",
        "listItem",
        "bulletList",
        "orderedList",
    }
    separator = "\n" if node.get("type") in block_types else " "

    return separator.join(part for part in parts if part).strip()


def extract_rich_text(raw_value: Any) -> Optional[str]:
    """
    Convert Jira rich text (ADF) or plain strings into a simple string.

    Returns None for empty/unknown inputs to avoid validation failures.
    """
    if raw_value is None:
        return None
    if isinstance(raw_value, str):
        return raw_value
    if isinstance(raw_value, dict):
        if raw_value.get("type") == "doc":
            segments: List[str] = []
            for node in raw_value.get("content", []) or []:
                text = _collect_adf_text(node)
                if text:
                    segments.append(text)
            flattened = "\n".join(segments).strip()
            return flattened or None
        flattened = _collect_adf_text(raw_value).strip()
        return flattened or None
    if isinstance(raw_value, list):
        segments: List[str] = []
        for item in raw_value:
            text = _collect_adf_text(item)
            if text:
                segments.append(text)
        flattened = "\n".join(segments).strip()
        return flattened or None
    return str(raw_value)


def parse_jira_user(user_data: Optional[Dict[str, Any]]) -> Optional[JiraUser]:
    """Parse Jira user data into JiraUser model."""
    if not user_data:
        return None
    return JiraUser(
        account_id=user_data.get("accountId"),
        account_type=user_data.get("accountType"),
        display_name=user_data.get("displayName"),
        email_address=user_data.get("emailAddress"),
        active=user_data.get("active"),
    )


def parse_jira_status(status_data: Optional[Dict[str, Any]]) -> Optional[JiraStatus]:
    """Parse Jira status data into JiraStatus model."""
    if not status_data:
        return None
    return JiraStatus(
        id=status_data.get("id", ""),
        name=status_data.get("name", ""),
        description=status_data.get("description"),
        status_category=status_data.get("statusCategory"),
    )


def parse_jira_priority(
    priority_data: Optional[Dict[str, Any]],
) -> Optional[JiraPriority]:
    """Parse Jira priority data into JiraPriority model."""
    if not priority_data:
        return None
    return JiraPriority(
        id=priority_data.get("id", ""),
        name=priority_data.get("name", ""),
        icon_url=priority_data.get("iconUrl"),
    )


def parse_jira_issue_type(
    issue_type_data: Optional[Dict[str, Any]],
) -> Optional[JiraIssueType]:
    """Parse Jira issue type data into JiraIssueType model."""
    if not issue_type_data:
        return None
    return JiraIssueType(
        id=issue_type_data.get("id", ""),
        name=issue_type_data.get("name", ""),
        description=issue_type_data.get("description"),
        icon_url=issue_type_data.get("iconUrl"),
    )


def parse_jira_project(project_data: Optional[Dict[str, Any]]) -> Optional[JiraProject]:
    """Parse Jira project data into JiraProject model."""
    if not project_data:
        return None
    return JiraProject(
        id=project_data.get("id", ""),
        key=project_data.get("key", ""),
        name=project_data.get("name", ""),
        project_type_key=project_data.get("projectTypeKey"),
    )


def parse_jira_attachment(attachment_data: Dict[str, Any]) -> JiraAttachment:
    """Parse Jira attachment data into JiraAttachment model."""
    return JiraAttachment(
        id=attachment_data.get("id", ""),
        filename=attachment_data.get("filename", ""),
        author=parse_jira_user(attachment_data.get("author")),
        created=parse_jira_datetime(attachment_data.get("created")),
        size=attachment_data.get("size"),
        mime_type=attachment_data.get("mimeType"),
        content=attachment_data.get("content"),
    )


def parse_jira_comment(comment_data: Dict[str, Any]) -> JiraComment:
    """Parse Jira comment data into JiraComment model."""
    return JiraComment(
        id=comment_data.get("id", ""),
        author=parse_jira_user(comment_data.get("author")),
        body=extract_rich_text(comment_data.get("body", "")) or "",
        created=parse_jira_datetime(comment_data.get("created")),
        updated=parse_jira_datetime(comment_data.get("updated")),
    )


def parse_jira_subtask(subtask_data: Dict[str, Any]) -> JiraSubtask:
    """Parse Jira subtask data into JiraSubtask model."""
    fields = subtask_data.get("fields", {})

    return JiraSubtask(
        id=subtask_data.get("id", ""),
        key=subtask_data.get("key", ""),
        fields=fields,
        summary=fields.get("summary"),
        description=extract_rich_text(fields.get("description")),
        status=parse_jira_status(fields.get("status")),
        assignee=parse_jira_user(fields.get("assignee")),
        reporter=parse_jira_user(fields.get("reporter")),
        priority=parse_jira_priority(fields.get("priority")),
        issue_type=parse_jira_issue_type(fields.get("issuetype")),
        created=parse_jira_datetime(fields.get("created")),
        updated=parse_jira_datetime(fields.get("updated")),
        labels=fields.get("labels", []),
        components=fields.get("components", []),
        comments=[
            parse_jira_comment(c) for c in fields.get("comment", {}).get("comments", [])
        ],
        attachments=[parse_jira_attachment(a) for a in fields.get("attachment", [])],
    )


def parse_jira_task(issue_data: Dict[str, Any]) -> JiraTask:
    """Parse Jira issue data into JiraTask model."""
    fields = issue_data.get("fields", {})

    return JiraTask(
        id=issue_data.get("id", ""),
        key=issue_data.get("key", ""),
        fields=fields,
        summary=fields.get("summary"),
        description=extract_rich_text(fields.get("description")),
        status=parse_jira_status(fields.get("status")),
        assignee=parse_jira_user(fields.get("assignee")),
        reporter=parse_jira_user(fields.get("reporter")),
        priority=parse_jira_priority(fields.get("priority")),
        issue_type=parse_jira_issue_type(fields.get("issuetype")),
        project=parse_jira_project(fields.get("project")),
        created=parse_jira_datetime(fields.get("created")),
        updated=parse_jira_datetime(fields.get("updated")),
        labels=fields.get("labels", []),
        components=fields.get("components", []),
        comments=[
            parse_jira_comment(c) for c in fields.get("comment", {}).get("comments", [])
        ],
        attachments=[parse_jira_attachment(a) for a in fields.get("attachment", [])],
        subtasks=[parse_jira_subtask(st) for st in fields.get("subtasks", [])],
    )


__all__ = [
    "extract_rich_text",
    "parse_jira_attachment",
    "parse_jira_comment",
    "parse_jira_datetime",
    "parse_jira_issue_type",
    "parse_jira_priority",
    "parse_jira_project",
    "parse_jira_status",
    "parse_jira_subtask",
    "parse_jira_task",
    "parse_jira_user",
]
