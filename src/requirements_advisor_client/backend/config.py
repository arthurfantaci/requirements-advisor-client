"""
Configuration management using pydantic-settings.

Loads settings from environment variables and .env file.
"""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # MCP Server
    mcp_server_url: str = "https://requirements-advisor-production.up.railway.app/mcp"

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/sessions.db"

    # Backend server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_json: bool = False

    # LLM API Keys (optional - at least one should be set)
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    google_api_key: str | None = None

    # Guardrails Configuration
    guardrails_enabled: bool = True
    guardrails_llm_provider: str = "gpt-3.5-turbo"
    guardrails_toxicity_threshold: float = 0.8
    guardrails_pii_entities: list[str] = [
        "EMAIL_ADDRESS",
        "PHONE_NUMBER",
        "US_SSN",
        "CREDIT_CARD",
        "IP_ADDRESS",
    ]
    guardrails_valid_topics: list[str] = [
        "requirements management",
        "requirements engineering",
        "traceability",
        "Jama Software",
        "Jama Connect",
        "INCOSE",
        "EARS notation",
        "system requirements",
        "software requirements",
        "verification",
        "validation",
        "requirements analysis",
        "requirements specification",
        "requirements elicitation",
        "stakeholder requirements",
        "functional requirements",
        "non-functional requirements",
        "requirements review",
        "requirements baseline",
        "change management",
        "impact analysis",
    ]
    guardrails_invalid_topics: list[str] = [
        "politics",
        "religion",
        "sports",
        "entertainment",
        "cooking",
        "travel",
        "fashion",
        "gaming",
        "cryptocurrency",
        "stock trading",
    ]

    @property
    def async_database_url(self) -> str:
        """Return the database URL converted for async drivers.

        Converts standard PostgreSQL URLs to use asyncpg driver.

        Returns:
            Database URL suitable for async SQLAlchemy.
        """
        url = self.database_url
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @property
    def data_dir(self) -> Path:
        """Return the data directory path.

        Creates the directory if it doesn't exist.

        Returns:
            Path to the data directory.
        """
        path = Path("./data")
        path.mkdir(parents=True, exist_ok=True)
        return path


# Global settings instance
settings = Settings()
