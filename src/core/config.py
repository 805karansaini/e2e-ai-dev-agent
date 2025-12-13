"""Application configuration powered by environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Base settings for the FastAPI service."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_HOST: str = Field(
        "0.0.0.0", description="Host interface for the FastAPI server"
    )
    APP_PORT: int = Field(8000, description="Port for the FastAPI server")
    LOG_LEVEL: str = Field(
        "INFO",
        description="Logging level for the application (e.g. DEBUG, INFO).",
    )

    CLINE_CLI_BIN: str = Field(
        "cline",
        description="CLINE CLI binary used to start tasks.",
    )
    CLINE_CLI_ARGS: List[str] = Field(
        default_factory=list,
        description="Additional arguments passed to the CLINE CLI invocation.",
    )
    DEFAULT_BASE_BRANCH: str = Field(
        "main",
        description="Default branch used when none is supplied in requests.",
    )
    TASK_WORKDIR: Optional[str] = Field(
        None,
        description="Working directory to execute CLINE CLI commands in.",
    )
    JIRA_BASE_URL: str = Field("", description="Base URL for the Jira instance.")
    JIRA_EMAIL: str = Field("", description="User email for Jira authentication.")
    JIRA_API_TOKEN: str = Field("", description="API token for Jira authentication.")
    JIRA_PROJECT_KEY: str = Field("", description="Default Jira project key.")
    JIRA_VERIFY_SSL: bool = Field(
        True, description="Whether to verify SSL certificates when calling Jira."
    )
    BACKEND_CORS_ORIGINS: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        description=(
            "Allowed CORS origins for the FastAPI backend. "
            "Override in .env (comma-separated or JSON list) for other frontends."
        ),
    )

    @property
    def log_level(self) -> str:
        """Compatibility alias for log level name."""

        return self.LOG_LEVEL


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached `Settings` instance."""

    return Settings()  # type: ignore[call-arg]


# Singleton settings instance for convenience imports
settings = get_settings()
