"""
Frontend configuration using pydantic-settings.

Loads frontend settings from environment variables.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class FrontendSettings(BaseSettings):
    """Frontend application settings.

    Attributes:
        api_url: Backend API URL for REST calls.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_url: str = "http://localhost:8000"


# Global settings instance
frontend_settings = FrontendSettings()
