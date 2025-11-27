"""
Centralized logging configuration using loguru.

Provides consistent logging setup across the application with support
for both human-readable and JSON output formats.
"""

import sys
from typing import Any

from loguru import logger


def setup_logging(
    level: str = "INFO",
    json_output: bool = False,
    log_file: str | None = None,
) -> Any:
    """Configure loguru for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        json_output: If True, output logs as JSON for production monitoring.
        log_file: Optional file path for log output with rotation.

    Returns:
        Configured logger instance.

    Example:
        >>> setup_logging(level="DEBUG", json_output=False)
        >>> logger.info("Application started")
    """
    # Remove default handler
    logger.remove()

    # Format for human-readable output
    human_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    # Add stderr handler
    if json_output:
        logger.add(
            sys.stderr,
            level=level,
            format="{message}",
            serialize=True,  # JSON serialization
        )
    else:
        logger.add(
            sys.stderr,
            level=level,
            format=human_format,
            colorize=True,
        )

    # Add optional file handler with rotation
    if log_file:
        logger.add(
            log_file,
            level=level,
            format=human_format if not json_output else "{message}",
            serialize=json_output,
            rotation="10 MB",
            retention="7 days",
            compression="gz",
        )

    return logger


def get_logger(name: str | None = None) -> Any:
    """Get a logger instance, optionally bound to a specific name.

    Args:
        name: Optional name to bind to the logger for context.

    Returns:
        Logger instance, optionally bound to the given name.

    Example:
        >>> log = get_logger("mcp_client")
        >>> log.info("Connected to server")
    """
    if name:
        return logger.bind(name=name)
    return logger
