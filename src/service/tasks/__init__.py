import os
from pathlib import Path

from src.core.config import settings

from .cli_executor import ClineExecutor
from .context_builder import JiraContextBuilder
from .executor import TaskExecutor
from .models import TaskPayload
from .orchestrator import TaskOrchestrator
from .persistence import TaskPersistence
from .prompt_builder import PromptBuilder
from .runner import TaskRunner, task_runner

_base_dir = Path(settings.TASK_WORKDIR or os.getcwd())
_attachments_dir = _base_dir / "data" / "jira_attachments"
_persistence = TaskPersistence(_attachments_dir)
_context_builder = JiraContextBuilder(_attachments_dir)
_prompt_builder = PromptBuilder(_base_dir, _attachments_dir)
_cli_executor = ClineExecutor(
    settings.CLINE_CLI_BIN, settings.CLINE_CLI_ARGS, settings.TASK_WORKDIR
)

task_orchestrator = TaskOrchestrator(
    prompt_builder=_prompt_builder,
    persistence=_persistence,
    executor=_cli_executor,
)
task_executor = TaskExecutor(executor=_cli_executor, persistence=_persistence)


async def build_and_persist_context(payload: TaskPayload):
    """Build Jira context for a payload and persist it to the task store.

    This is the shared "build context -> persist" flow used by the runner,
    exposed as a lightweight helper for API routes and internal callers.
    """

    context = await _context_builder.build(payload)
    await _persistence.persist(context, payload)
    return context


__all__ = [
    "TaskPayload",
    "TaskRunner",
    "task_runner",
    "TaskOrchestrator",
    "task_orchestrator",
    "TaskExecutor",
    "task_executor",
    "build_and_persist_context",
]
