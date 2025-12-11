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
_persistence = TaskPersistence(_base_dir / "data" / "tasks.db", _attachments_dir)
_context_builder = JiraContextBuilder(_attachments_dir)
_prompt_builder = PromptBuilder(_base_dir, _attachments_dir)
_cli_executor = ClineExecutor(
    settings.CLINE_CLI_BIN, settings.CLINE_CLI_ARGS, settings.TASK_WORKDIR
)

task_orchestrator = TaskOrchestrator(
    context_builder=_context_builder,
    prompt_builder=_prompt_builder,
    persistence=_persistence,
    executor=_cli_executor,
)
task_executor = TaskExecutor(executor=_cli_executor, persistence=_persistence)

__all__ = [
    "TaskPayload",
    "TaskRunner",
    "task_runner",
    "TaskOrchestrator",
    "task_orchestrator",
    "TaskExecutor",
    "task_executor",
]
