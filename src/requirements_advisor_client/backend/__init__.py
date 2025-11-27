"""
Backend module for Requirements Advisor Client.

Provides FastAPI application with MCP client and multi-LLM support.
"""

from requirements_advisor_client.backend.config import settings
from requirements_advisor_client.backend.logging import get_logger, setup_logging

__all__ = ["settings", "setup_logging", "get_logger"]
