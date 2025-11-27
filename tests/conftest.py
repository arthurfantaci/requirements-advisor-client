"""
Pytest fixtures and configuration for the test suite.

Provides shared fixtures for mocking MCP client, LLM responses,
database sessions, and FastAPI test client.
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from requirements_advisor_client.backend.database import Base


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session.

    Yields:
        Event loop for async tests.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    """Create mock settings for testing.

    Returns:
        Mock settings object with test configuration.
    """
    settings = MagicMock()
    settings.mcp_server_url = "https://test-server.example.com/mcp"
    settings.database_url = "sqlite+aiosqlite:///:memory:"
    settings.async_database_url = "sqlite+aiosqlite:///:memory:"
    settings.backend_host = "0.0.0.0"
    settings.backend_port = 8000
    settings.log_level = "DEBUG"
    settings.log_json = False
    settings.data_dir.return_value = "/tmp/test_data"
    return settings


@pytest.fixture
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """Create an in-memory database for testing.

    Yields:
        Async database session for test operations.
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def mock_mcp_client() -> MagicMock:
    """Create a mock MCP client for testing.

    Returns:
        Mock MCP client with preset responses.
    """
    client = MagicMock()
    client.is_connected = True
    client.server_url = "https://test-server.example.com/mcp"

    # Mock tool list
    mock_tool = MagicMock()
    mock_tool.name = "search_requirements"
    mock_tool.description = "Search requirements guidance"
    mock_tool.inputSchema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
        },
        "required": ["query"],
    }

    client.list_tools = AsyncMock(return_value=[mock_tool])

    # Mock tool call result
    mock_result = MagicMock()
    mock_content = MagicMock()
    mock_content.text = "Test search result content"
    mock_result.content = [mock_content]
    client.call_tool = AsyncMock(return_value=mock_result)

    client.connect = AsyncMock()
    client.disconnect = AsyncMock()

    return client


@pytest.fixture
def mock_litellm_response() -> MagicMock:
    """Create a mock LiteLLM response for testing.

    Returns:
        Mock LLM response without tool calls.
    """
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message = MagicMock()
    response.choices[0].message.content = "This is a test response from the LLM."
    response.choices[0].message.tool_calls = None
    return response


@pytest.fixture
def mock_litellm_tool_call_response() -> MagicMock:
    """Create a mock LiteLLM response with tool calls.

    Returns:
        Mock LLM response with a tool call.
    """
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message = MagicMock()
    response.choices[0].message.content = None

    # Mock tool call
    tool_call = MagicMock()
    tool_call.id = "call_123"
    tool_call.function = MagicMock()
    tool_call.function.name = "search_requirements"
    tool_call.function.arguments = '{"query": "test query"}'

    response.choices[0].message.tool_calls = [tool_call]
    response.choices[0].message.model_dump = MagicMock(
        return_value={
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_123",
                    "function": {
                        "name": "search_requirements",
                        "arguments": '{"query": "test query"}',
                    },
                }
            ],
        }
    )

    return response


@pytest.fixture
def test_client(mock_mcp_client: MagicMock) -> Generator[TestClient, None, None]:
    """Create a FastAPI test client with mocked dependencies.

    Args:
        mock_mcp_client: Mocked MCP client fixture.

    Yields:
        FastAPI TestClient for API testing.
    """
    with patch(
        "requirements_advisor_client.backend.main.mcp_client",
        mock_mcp_client,
    ):
        from requirements_advisor_client.backend.main import app

        with TestClient(app) as client:
            yield client


@pytest.fixture
def sample_chat_request() -> dict[str, Any]:
    """Create a sample chat request for testing.

    Returns:
        Dictionary representing a chat request.
    """
    return {
        "message": "What is EARS notation?",
        "session_id": None,
        "provider": "claude",
        "history": [],
    }


@pytest.fixture
def sample_chat_history() -> list[dict[str, str]]:
    """Create sample chat history for testing.

    Returns:
        List of message dictionaries.
    """
    return [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi! How can I help you with requirements?"},
        {"role": "user", "content": "Tell me about traceability"},
    ]
