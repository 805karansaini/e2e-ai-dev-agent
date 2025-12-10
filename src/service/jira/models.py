from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class JiraUser(BaseModel):
    """Jira user information."""

    account_id: Optional[str] = None
    account_type: Optional[str] = None
    display_name: Optional[str] = None
    email_address: Optional[str] = None
    active: Optional[bool] = None


class JiraStatus(BaseModel):
    """Jira status information."""

    id: str
    name: str
    description: Optional[str] = None
    status_category: Optional[Dict[str, Any]] = None


class JiraPriority(BaseModel):
    """Jira priority information."""

    id: str
    name: str
    icon_url: Optional[str] = None


class JiraIssueType(BaseModel):
    """Jira issue type information."""

    id: str
    name: str
    description: Optional[str] = None
    icon_url: Optional[str] = None


class JiraProject(BaseModel):
    """Jira project information."""

    id: str
    key: str
    name: str
    project_type_key: Optional[str] = None


class JiraAttachment(BaseModel):
    """Jira attachment information."""

    id: str
    filename: str
    author: Optional[JiraUser] = None
    created: Optional[datetime] = None
    size: Optional[int] = None
    mime_type: Optional[str] = None
    content: Optional[str] = None  # URL to download the attachment


class JiraComment(BaseModel):
    """Jira comment information."""

    id: str
    author: Optional[JiraUser] = None
    body: str
    created: Optional[datetime] = None
    updated: Optional[datetime] = None


class JiraSubtask(BaseModel):
    """Jira subtask information."""

    id: str
    key: str
    fields: Dict[str, Any] = Field(default_factory=dict)

    # Extracted fields for convenience
    summary: Optional[str] = None
    description: Optional[str] = None
    status: Optional[JiraStatus] = None
    assignee: Optional[JiraUser] = None
    reporter: Optional[JiraUser] = None
    priority: Optional[JiraPriority] = None
    issue_type: Optional[JiraIssueType] = None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None
    labels: List[str] = Field(default_factory=list)
    components: List[Dict[str, Any]] = Field(default_factory=list)
    comments: List[JiraComment] = Field(default_factory=list)
    attachments: List[JiraAttachment] = Field(default_factory=list)


class JiraTask(BaseModel):
    """Jira task/issue information."""

    id: str
    key: str
    fields: Dict[str, Any] = Field(default_factory=dict)

    # Extracted fields for convenience
    summary: Optional[str] = None
    description: Optional[str] = None
    status: Optional[JiraStatus] = None
    assignee: Optional[JiraUser] = None
    reporter: Optional[JiraUser] = None
    priority: Optional[JiraPriority] = None
    issue_type: Optional[JiraIssueType] = None
    project: Optional[JiraProject] = None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None
    labels: List[str] = Field(default_factory=list)
    components: List[Dict[str, Any]] = Field(default_factory=list)
    comments: List[JiraComment] = Field(default_factory=list)
    attachments: List[JiraAttachment] = Field(default_factory=list)
    subtasks: List[JiraSubtask] = Field(default_factory=list)


__all__ = [
    "JiraAttachment",
    "JiraComment",
    "JiraIssueType",
    "JiraPriority",
    "JiraProject",
    "JiraStatus",
    "JiraSubtask",
    "JiraTask",
    "JiraUser",
]
