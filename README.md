# E2E AI Dev Agent

An end-to-end AI development agent that orchestrates task execution using CLINE CLI, integrates with Jira for task management, and provides a FastAPI backend for task orchestration and execution.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Configuration](#configuration)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [API Endpoints](#api-endpoints)

---

## Overview

This project provides an automated development workflow that:

1. **Imports tasks from Jira** — Fetches issues, subtasks, and attachments
2. **Generates execution prompts** — Uses LLM to create actionable prompts
3. **Executes tasks via CLINE CLI** — Runs the generated prompts through the CLINE agent
4. **Tracks progress** — Persists task state in SQLite and updates status throughout execution

---

## Features

- **Jira Integration**: Fetch tasks, subtasks, comments, and attachments from Jira Cloud
- **LLM-Powered Orchestration**: Generate structured prompts using OpenRouter (OpenAI-compatible)
- **Task Queue**: Background worker for sequential task execution
- **File Conversion**: Automatically converts PDF, DOCX, PPTX attachments to Markdown
- **RESTful API**: Full CRUD operations for tasks with filtering and pagination
- **Health Checks**: Liveness and readiness probes for deployment monitoring

---

## Configuration

Create a `.env` file using `.env.example` as a template and fill in the required values.

### Jira/Atlassian API Token Authentication

Go to https://id.atlassian.com/manage-profile/security/api-tokens
Click Create API token, name it
Copy the token immediately

### Required Environment Variables

| Variable             | Description                                 |
| -------------------- | ------------------------------------------- |
| `OPENROUTER_API_KEY` | OpenRouter API key for LLM calls (required) |
| `JIRA_BASE_URL`      | Base URL for your Jira instance             |
| `JIRA_EMAIL`         | User email for Jira authentication          |
| `JIRA_API_TOKEN`     | API token for Jira authentication           |
| `JIRA_PROJECT_KEY`   | Default Jira project key                    |

### Optional Environment Variables

| Variable                     | Default                     | Description                                 |
| ---------------------------- | --------------------------- | ------------------------------------------- |
| `DATABASE_URL`               | `sqlite:///./data/tasks.db` | SQLAlchemy database URL (SQLite only)       |
| `APP_HOST`                   | `0.0.0.0`                   | Host interface for the FastAPI server       |
| `APP_PORT`                   | `8080`                      | Port for the FastAPI server                 |
| `LOG_LEVEL`                  | `INFO`                      | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `CLINE_CLI_BIN`              | `cline`                     | Path to CLINE CLI binary                    |
| `DEFAULT_BASE_BRANCH`        | `main`                      | Default Git branch for tasks                |
| `TASK_WORKDIR`               | Current directory           | Working directory for CLINE execution       |
| `OPENROUTER_MODEL`           | `openai/gpt-5-nano`         | Default OpenRouter model identifier         |
| `OPENROUTER_TIMEOUT_SECONDS` | `600.0`                     | Timeout for OpenRouter requests             |

### CORS Configuration

| Variable                    | Description                                           |
| --------------------------- | ----------------------------------------------------- |
| `BACKEND_CORS_ORIGINS`      | Comma-separated list or JSON array of allowed origins |
| `BACKEND_CORS_ORIGIN_REGEX` | Optional regex for allowed origins (takes precedence) |

Example for Vercel + ngrok:

```bash
BACKEND_CORS_ORIGINS=["https://frontend-sage-eight-38.vercel.app"]
BACKEND_CORS_ORIGIN_REGEX=https://.*\.ngrok-free\.app
```

---

## Getting Started

### Prerequisites

#### Platform Support

- macOS
- Linux (x86_64)

#### System Dependencies

- `cat`, `jq`, `gh`, `git` - Command-line tools (typically pre-installed on macOS/Linux)
- CLINE CLI installed and available in PATH

#### Software Requirements

- Python 3.12+
- Jira Cloud account with API access

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd e2e-ai-dev-agent

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Run the server
python main.py
```

### Running Tests

```bash
pytest tests/
```

---

## Task Workflow

1. **Import from Jira**: Call `/db/tasks/import-from-jira` with a Jira issue key
2. **Orchestrate**: Call `/tasks/orchestrator` to generate LLM prompts
3. **Execute**: Call `/tasks/start` to run prompts via CLINE CLI
4. **Monitor**: Check task status via `/db/tasks/{task_id}`

Or use `/tasks/auto` for a single-call workflow that handles orchestration and execution.

---

## Project Structure

```
e2e-ai-dev-agent/
├── .github/
│   └── workflows/
│       └── agent-trigger.yml      # GitHub Actions workflow for PR/issue triggers
├── data/                          # SQLite database storage (gitignored)
├── prompts/                       # Prompt templates for orchestration
│   ├── create_pull_request.md     # Template for PR creation prompts
│   ├── high_level_review.md       # Template for code review prompts
│   ├── orchestration_prompt.md    # Main orchestration prompt template
│   ├── orchestration_prompt_v1.md # Versioned orchestration prompt
│   └── orchestration_prompt_v1 copy.md  # Backup copy
├── script_log/                    # CLINE execution logs (gitignored)
├── src/                           # Main source code
│   ├── __init__.py                # Package marker
│   ├── api/                       # FastAPI application layer
│   │   ├── __init__.py            # Package marker
│   │   ├── app.py                 # FastAPI application factory and configuration
│   │   ├── middleware.py          # Request logging and correlation ID middleware
│   │   ├── routes/                # API route handlers
│   │   │   ├── __init__.py        # Route exports (health_router, task_execution_router, etc.)
│   │   │   ├── health.py          # Health check endpoints (/health/liveness, /health/readiness)
│   │   │   ├── task_execution.py  # Task orchestration endpoints (/tasks/orchestrator, /tasks/start, /tasks/auto)
│   │   │   └── task_records.py    # Database CRUD endpoints (/db/tasks/*)
│   │   ├── schemas/               # Pydantic request/response models
│   │   │   ├── __init__.py        # Schema exports
│   │   │   ├── db_tasks.py        # Database task schemas (CreateTask, TaskResponse, TaskList, etc.)
│   │   │   ├── envelopes.py       # Standard API response wrappers (Success, ErrorResponse)
│   │   │   ├── health.py          # Health check response schemas (LivenessStatus, ReadinessStatus)
│   │   │   └── tasks.py           # Task execution schemas (TaskCreateRequest, TaskPlanResponse, etc.)
│   │   └── services/              # API service layer
│   │       ├── __init__.py        # Service exports
│   │       ├── jira_import_service.py  # Jira import business logic for API routes
│   │       └── task_service.py    # Task CRUD service with error handling
│   ├── core/                      # Core application configuration
│   │   ├── __init__.py            # Package marker
│   │   ├── config.py              # Pydantic settings and environment configuration
│   │   └── logging_config.py      # Loguru logging setup with uvicorn integration
│   ├── scripts/                   # Shell scripts for CLINE execution
│   │   ├── github_issue_using_cline.sh      # Script to create GitHub issues via CLINE
│   │   ├── render_cline_log.sh              # Render CLINE logs to human-readable format
│   │   ├── render_cline_log_v1.sh           # Version 1 of log renderer
│   │   ├── render_cline_log_v2.sh           # Version 2 of log renderer
│   │   ├── run_cline_task.sh                # Main CLINE task runner script
│   │   ├── run_cline_task_v1.sh             # Version 1 with JSON stream logging
│   │   ├── run_cline_task_v2.sh             # Version 2 of task runner
│   │   └── run_multitask_cline_agent.sh     # Multi-task CLINE execution script
│   └── service/                   # Business logic and integrations
│       ├── database_handler/      # SQLAlchemy database layer
│       │   ├── __init__.py        # Database exports (create_tables, TaskCRUD, etc.)
│       │   ├── config.py          # Database engine and session configuration
│       │   ├── crud.py            # Task CRUD operations (TaskCRUD class)
│       │   └── models/            # SQLAlchemy ORM models
│       │       ├── __init__.py    # Model exports (Base, Task, TaskStatus, TaskType)
│       │       ├── base.py        # SQLAlchemy declarative base
│       │       └── task.py        # Task model with status/type enums
│       ├── file_converter.py      # File conversion utilities (PDF/DOCX/PPTX to Markdown)
│       ├── jira/                  # Jira integration
│       │   ├── __init__.py        # Jira exports (JiraClient, models, parsers)
│       │   ├── client.py          # Async Jira API client (fetch issues, download attachments)
│       │   ├── import_utils.py    # Jira import helpers (attachment splitting, metadata extraction)
│       │   ├── models.py          # Pydantic models for Jira entities (JiraTask, JiraSubtask, etc.)
│       │   ├── parsers.py         # Jira API response parsers (ADF to text, datetime parsing)
│       │   └── prompt_models.py   # Jira context models for orchestration (JiraContext, SubtaskPrompt)
│       ├── llm/                   # LLM integration
│       │   ├── __init__.py        # LLM exports (OpenRouterLLM)
│       │   └── openrouter.py      # OpenRouter client with JSON schema support
│       └── tasks/                 # Task orchestration and execution
│           ├── __init__.py        # Task exports (task_orchestrator, task_executor, task_runner)
│           ├── cli_executor.py    # CLINE CLI subprocess executor with streaming output
│           ├── context_builder.py # Jira context builder (fetch + render task descriptions)
│           ├── executor.py        # Task executor with background worker queue
│           ├── models.py          # Task domain models (TaskPayload, OrchestrationResult, etc.)
│           ├── orchestrator.py    # Task orchestrator (LLM prompt generation + persistence)
│           ├── persistence.py     # Task persistence layer (SQLite upsert/load operations)
│           ├── prompt_builder.py  # Orchestration prompt composer with templates
│           └── runner.py          # Async task runner with queue management
├── tests/                         # Test suite
│   ├── conftest.py                # Pytest configuration and path setup
│   ├── test_api_health.py         # Health endpoint tests
│   └── test_jira_models.py        # Jira model and parser tests
├── main.py                        # Application entrypoint (uvicorn server)
├── README.md                      # This file
├── requirements.txt               # Python dependencies
└── ruff.toml                      # Ruff linter configuration
```

---

### Prompt Templates (`prompts/`)

| File                         | Description                                |
| ---------------------------- | ------------------------------------------ |
| `orchestration_prompt.md`    | Main orchestration prompt template for LLM |
| `orchestration_prompt_v1.md` | Versioned orchestration prompt             |
| `high_level_review.md`       | Template for code review follow-up prompts |
| `create_pull_request.md`     | Template for PR creation follow-up prompts |

---

## API Endpoints

### Health Checks

| Method | Endpoint            | Description                                          |
| ------ | ------------------- | ---------------------------------------------------- |
| GET    | `/health/liveness`  | Basic liveness probe                                 |
| GET    | `/health/readiness` | Readiness probe (checks CLINE CLI and worker status) |

### Task Execution

| Method | Endpoint              | Description                                                 |
| ------ | --------------------- | ----------------------------------------------------------- |
| POST   | `/tasks/orchestrator` | Generate prompts and execution plan for a task              |
| POST   | `/tasks/start`        | Start execution using stored prompts                        |
| POST   | `/tasks/auto`         | Orchestrate and start execution in one request (background) |

### Task Records (Database CRUD)

| Method | Endpoint                           | Description                              |
| ------ | ---------------------------------- | ---------------------------------------- |
| POST   | `/db/tasks`                        | Create a new task                        |
| POST   | `/db/tasks/sub-task`               | Create a new sub-task                    |
| GET    | `/db/tasks`                        | List tasks with filtering and pagination |
| GET    | `/db/tasks/{task_id}`              | Get a task by ID                         |
| GET    | `/db/tasks/sub-task/{sub_task_id}` | Get a sub-task by ID                     |
| PUT    | `/db/tasks/{task_id}`              | Update a task                            |
| PUT    | `/db/tasks/sub-task/{sub_task_id}` | Update a sub-task                        |
| DELETE | `/db/tasks/{task_id}`              | Delete a task                            |
| DELETE | `/db/tasks/sub-task/{sub_task_id}` | Delete a sub-task                        |
| POST   | `/db/tasks/import-from-jira`       | Import a task from Jira                  |

---
