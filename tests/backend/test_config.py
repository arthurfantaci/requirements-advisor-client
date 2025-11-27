"""Tests for the configuration module."""

import os
from unittest.mock import patch

import pytest


class TestSettings:
    """Test cases for the Settings class."""

    def test_default_settings(self):
        """Test that default settings are loaded correctly."""
        from requirements_advisor_client.backend.config import Settings

        settings = Settings()

        assert settings.mcp_server_url == "https://requirements-advisor-production.up.railway.app/mcp"
        assert "sqlite" in settings.database_url
        assert settings.backend_host == "0.0.0.0"
        assert settings.backend_port == 8000
        assert settings.log_level == "INFO"
        assert settings.log_json is False

    def test_settings_from_env(self):
        """Test that settings can be loaded from environment variables."""
        from requirements_advisor_client.backend.config import Settings

        env_vars = {
            "MCP_SERVER_URL": "https://custom-server.example.com/mcp",
            "DATABASE_URL": "postgresql://user:pass@localhost/db",
            "BACKEND_PORT": "9000",
            "LOG_LEVEL": "DEBUG",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            settings = Settings()

            assert settings.mcp_server_url == "https://custom-server.example.com/mcp"
            assert settings.database_url == "postgresql://user:pass@localhost/db"
            assert settings.backend_port == 9000
            assert settings.log_level == "DEBUG"

    def test_async_database_url_postgres_conversion(self):
        """Test that PostgreSQL URLs are converted for async driver."""
        from requirements_advisor_client.backend.config import Settings

        with patch.dict(
            os.environ,
            {"DATABASE_URL": "postgres://user:pass@localhost/db"},
            clear=False,
        ):
            settings = Settings()
            assert settings.async_database_url == "postgresql+asyncpg://user:pass@localhost/db"

    def test_async_database_url_postgresql_conversion(self):
        """Test that postgresql:// URLs are converted for async driver."""
        from requirements_advisor_client.backend.config import Settings

        with patch.dict(
            os.environ,
            {"DATABASE_URL": "postgresql://user:pass@localhost/db"},
            clear=False,
        ):
            settings = Settings()
            assert settings.async_database_url == "postgresql+asyncpg://user:pass@localhost/db"

    def test_async_database_url_sqlite_unchanged(self):
        """Test that SQLite URLs remain unchanged."""
        from requirements_advisor_client.backend.config import Settings

        with patch.dict(
            os.environ,
            {"DATABASE_URL": "sqlite+aiosqlite:///./data/sessions.db"},
            clear=False,
        ):
            settings = Settings()
            assert settings.async_database_url == "sqlite+aiosqlite:///./data/sessions.db"

    def test_data_dir_property(self, tmp_path):
        """Test that data_dir creates directory if needed."""
        from requirements_advisor_client.backend.config import Settings

        settings = Settings()
        data_dir = settings.data_dir

        assert data_dir.exists()
        assert data_dir.is_dir()
