"""Tests for the main FastAPI application."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Test cases for the health check endpoint."""

    def test_health_check_mcp_connected(self):
        """Test health check when MCP is connected."""
        mock_client = MagicMock()
        mock_client.is_connected = True

        with patch(
            "requirements_advisor_client.backend.main.mcp_client",
            mock_client,
        ):
            from requirements_advisor_client.backend.main import app

            with TestClient(app) as client:
                response = client.get("/health")

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
                assert data["mcp_connected"] is True
                assert "version" in data

    def test_health_check_mcp_disconnected(self):
        """Test health check when MCP is disconnected."""
        with patch(
            "requirements_advisor_client.backend.main.mcp_client",
            None,
        ):
            from requirements_advisor_client.backend.main import app

            with TestClient(app) as client:
                response = client.get("/health")

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
                assert data["mcp_connected"] is False


class TestToolsEndpoint:
    """Test cases for the tools listing endpoint."""

    def test_list_tools_success(self, mock_mcp_client):
        """Test listing tools when MCP is connected."""
        with patch(
            "requirements_advisor_client.backend.main.mcp_client",
            mock_mcp_client,
        ):
            from requirements_advisor_client.backend.main import app

            with TestClient(app) as client:
                response = client.get("/tools")

                assert response.status_code == 200
                tools = response.json()
                assert len(tools) == 1
                assert tools[0]["name"] == "search_requirements"

    def test_list_tools_not_connected(self):
        """Test listing tools when MCP is not connected."""
        with patch(
            "requirements_advisor_client.backend.main.mcp_client",
            None,
        ):
            from requirements_advisor_client.backend.main import app

            with TestClient(app) as client:
                response = client.get("/tools")

                assert response.status_code == 503
                assert "not connected" in response.json()["detail"].lower()


class TestChatEndpoint:
    """Test cases for the chat endpoint."""

    @pytest.mark.asyncio
    async def test_chat_success(
        self,
        mock_mcp_client,
        mock_litellm_response,
        sample_chat_request,
    ):
        """Test successful chat request."""
        with patch(
            "requirements_advisor_client.backend.main.mcp_client",
            mock_mcp_client,
        ), patch(
            "requirements_advisor_client.backend.main.get_or_create_session",
            AsyncMock(return_value="test-session-id"),
        ), patch(
            "requirements_advisor_client.backend.main.save_message",
            AsyncMock(),
        ), patch(
            "requirements_advisor_client.backend.llm.litellm"
        ) as mock_litellm:
            mock_litellm.completion.return_value = mock_litellm_response

            from requirements_advisor_client.backend.main import app

            with TestClient(app) as client:
                response = client.post("/chat", json=sample_chat_request)

                assert response.status_code == 200
                data = response.json()
                assert "response" in data
                assert "session_id" in data

    def test_chat_invalid_provider(self, sample_chat_request):
        """Test chat with invalid provider returns error."""
        sample_chat_request["provider"] = "invalid_provider"

        with patch(
            "requirements_advisor_client.backend.main.mcp_client",
            MagicMock(is_connected=True, list_tools=AsyncMock(return_value=[])),
        ), patch(
            "requirements_advisor_client.backend.main.get_or_create_session",
            AsyncMock(return_value="test-session"),
        ):
            from requirements_advisor_client.backend.main import app

            with TestClient(app) as client:
                response = client.post("/chat", json=sample_chat_request)

                assert response.status_code == 400
                assert "unsupported" in response.json()["detail"].lower()

    def test_chat_with_history(self, sample_chat_request, sample_chat_history):
        """Test chat request with conversation history."""
        sample_chat_request["history"] = sample_chat_history

        with patch(
            "requirements_advisor_client.backend.main.mcp_client",
            MagicMock(is_connected=True, list_tools=AsyncMock(return_value=[])),
        ), patch(
            "requirements_advisor_client.backend.main.get_or_create_session",
            AsyncMock(return_value="test-session"),
        ), patch(
            "requirements_advisor_client.backend.main.save_message",
            AsyncMock(),
        ), patch(
            "requirements_advisor_client.backend.llm.litellm"
        ) as mock_litellm:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Response with history"
            mock_response.choices[0].message.tool_calls = None
            mock_litellm.completion.return_value = mock_response

            from requirements_advisor_client.backend.main import app

            with TestClient(app) as client:
                response = client.post("/chat", json=sample_chat_request)

                assert response.status_code == 200
                # Verify history was included in LLM call
                call_args = mock_litellm.completion.call_args
                messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
                # System message + history + user message
                assert len(messages) >= 4


class TestHistoryEndpoint:
    """Test cases for the history endpoint."""

    @pytest.mark.asyncio
    async def test_get_history_success(self):
        """Test retrieving chat history."""
        mock_history = [
            {
                "role": "user",
                "content": "Hello",
                "created_at": "2024-01-01T00:00:00",
            },
            {
                "role": "assistant",
                "content": "Hi there!",
                "created_at": "2024-01-01T00:00:01",
            },
        ]

        with patch(
            "requirements_advisor_client.backend.main.get_history",
            AsyncMock(return_value=mock_history),
        ):
            from requirements_advisor_client.backend.main import app

            with TestClient(app) as client:
                response = client.get("/history/test-session-id")

                assert response.status_code == 200
                data = response.json()
                assert len(data) == 2
                assert data[0]["role"] == "user"
                assert data[1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_get_history_empty(self):
        """Test retrieving empty history."""
        with patch(
            "requirements_advisor_client.backend.main.get_history",
            AsyncMock(return_value=[]),
        ):
            from requirements_advisor_client.backend.main import app

            with TestClient(app) as client:
                response = client.get("/history/nonexistent-session")

                assert response.status_code == 200
                assert response.json() == []


class TestSessionMiddleware:
    """Test cases for the session middleware."""

    def test_session_cookie_created(self):
        """Test that session cookie is created for new requests."""
        with patch(
            "requirements_advisor_client.backend.main.mcp_client",
            None,
        ):
            from requirements_advisor_client.backend.main import app

            with TestClient(app) as client:
                response = client.get("/health")

                assert response.status_code == 200
                # Check that session_id cookie is set
                cookies = response.cookies
                assert "session_id" in cookies

    def test_session_cookie_preserved(self):
        """Test that existing session cookie is preserved."""
        with patch(
            "requirements_advisor_client.backend.main.mcp_client",
            None,
        ):
            from requirements_advisor_client.backend.main import app

            with TestClient(app) as client:
                # First request creates cookie
                response1 = client.get("/health")
                session_id = response1.cookies.get("session_id")

                # Second request should use same session
                response2 = client.get("/health")

                assert response2.cookies.get("session_id") == session_id
