#!/usr/bin/env python3
"""Test script for Jira Pydantic models and parsing functions."""

import sys
from pathlib import Path

# Allow running tests without installing the package
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.append(str(SRC_PATH))

from service.jira import (  # noqa: E402
    parse_jira_attachment,
    parse_jira_comment,
    parse_jira_datetime,
    parse_jira_issue_type,
    parse_jira_priority,
    parse_jira_project,
    parse_jira_status,
    parse_jira_subtask,
    parse_jira_task,
    parse_jira_user,
)


def test_jira_models():
    """Test Jira Pydantic models creation and parsing."""

    # Test JiraUser
    user_data = {
        "accountId": "12345",
        "accountType": "atlassian",
        "displayName": "John Doe",
        "emailAddress": "john.doe@example.com",
        "active": True,
    }
    user = parse_jira_user(user_data)
    assert user is not None
    assert user.display_name == "John Doe"
    assert user.email_address == "john.doe@example.com"

    # Test JiraStatus
    status_data = {
        "id": "10000",
        "name": "To Do",
        "description": "Issue is open and ready to be worked on",
        "statusCategory": {"id": 2, "key": "new", "name": "To Do"},
    }
    status = parse_jira_status(status_data)
    assert status is not None
    assert status.name == "To Do"

    # Test JiraPriority
    priority_data = {
        "id": "1",
        "name": "Highest",
        "iconUrl": "https://example.com/priority-highest.png",
    }
    priority = parse_jira_priority(priority_data)
    assert priority is not None
    assert priority.name == "Highest"

    # Test JiraIssueType
    issue_type_data = {
        "id": "10001",
        "name": "Bug",
        "description": "A problem which impairs or prevents the functions of the product.",
        "iconUrl": "https://example.com/bug-icon.png",
    }
    issue_type = parse_jira_issue_type(issue_type_data)
    assert issue_type is not None
    assert issue_type.name == "Bug"

    # Test JiraProject
    project_data = {
        "id": "10000",
        "key": "PROJ",
        "name": "Sample Project",
        "projectTypeKey": "software",
    }
    project = parse_jira_project(project_data)
    assert project is not None
    assert project.key == "PROJ"

    # Test JiraAttachment
    attachment_data = {
        "id": "10001",
        "filename": "screenshot.png",
        "author": user_data,
        "created": "2023-12-01T10:30:00.000+0000",
        "size": 1024000,
        "mimeType": "image/png",
        "content": "https://example.com/attachment/10001",
    }
    attachment = parse_jira_attachment(attachment_data)
    assert attachment.filename == "screenshot.png"
    assert attachment.size == 1024000

    # Test JiraComment with Atlassian doc body
    comment_data = {
        "id": "10002",
        "author": user_data,
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "This is a test comment"}],
                }
            ],
        },
        "created": "2023-12-01T10:30:00.000+0000",
        "updated": "2023-12-01T11:00:00.000+0000",
    }
    comment = parse_jira_comment(comment_data)
    assert comment.body == "This is a test comment"
    assert comment.author.display_name == "John Doe"

    # Sample ADF description to mimic Jira Cloud rich text
    adf_description = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": "Implement user authentication for the web app",
                    }
                ],
            },
            {
                "type": "bulletList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": "Add login and logout flows",
                                    }
                                ],
                            }
                        ],
                    }
                ],
            },
        ],
    }
    expected_description = (
        "Implement user authentication for the web app\nAdd login and logout flows"
    )

    # Test JiraSubtask
    subtask_data = {
        "id": "10003",
        "key": "PROJ-456",
        "fields": {
            "summary": "Implement login functionality",
            "description": adf_description,
            "status": status_data,
            "assignee": user_data,
            "reporter": user_data,
            "priority": priority_data,
            "issuetype": issue_type_data,
            "created": "2023-12-01T09:00:00.000+0000",
            "updated": "2023-12-01T10:00:00.000+0000",
            "labels": ["backend", "authentication"],
            "components": [{"name": "Web App"}],
            "comment": {"comments": [comment_data]},
            "attachment": [attachment_data],
        },
    }
    subtask = parse_jira_subtask(subtask_data)
    assert subtask.key == "PROJ-456"
    assert subtask.summary == "Implement login functionality"
    assert subtask.status.name == "To Do"
    assert subtask.description == expected_description
    assert len(subtask.comments) == 1
    assert len(subtask.attachments) == 1

    # Test JiraTask
    task_data = {
        "id": "10004",
        "key": "PROJ-123",
        "fields": {
            "summary": "Implement user authentication system",
            "description": adf_description,
            "status": status_data,
            "assignee": user_data,
            "reporter": user_data,
            "priority": priority_data,
            "issuetype": {"id": "10002", "name": "Story"},
            "project": project_data,
            "created": "2023-12-01T08:00:00.000+0000",
            "updated": "2023-12-01T12:00:00.000+0000",
            "labels": ["backend", "security"],
            "components": [{"name": "Web App"}, {"name": "API"}],
            "comment": {"comments": [comment_data]},
            "attachment": [attachment_data],
            "subtasks": [subtask_data],
        },
    }
    task = parse_jira_task(task_data)
    assert task.key == "PROJ-123"
    assert task.summary == "Implement user authentication system"
    assert task.project.key == "PROJ"
    assert task.description == expected_description
    assert len(task.subtasks) == 1
    assert task.subtasks[0].key == "PROJ-456"

    # Test datetime parsing
    datetime_str = "2023-12-01T10:30:00.000+0000"
    parsed_dt = parse_jira_datetime(datetime_str)
    assert parsed_dt is not None
    assert parsed_dt.year == 2023
    assert parsed_dt.month == 12
