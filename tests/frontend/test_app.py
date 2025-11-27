"""Tests for the Streamlit frontend application."""

from unittest.mock import MagicMock, patch

import pytest


class TestFrontendConfig:
    """Test cases for frontend configuration."""

    def test_default_api_url(self):
        """Test default API URL is localhost."""
        from requirements_advisor_client.frontend.config import FrontendSettings

        settings = FrontendSettings()
        assert settings.api_url == "http://localhost:8000"

    def test_api_url_from_env(self):
        """Test API URL can be set from environment."""
        import os

        with patch.dict(os.environ, {"API_URL": "http://backend:8000"}):
            from requirements_advisor_client.frontend.config import FrontendSettings

            settings = FrontendSettings()
            assert settings.api_url == "http://backend:8000"


class TestBackendHealthCheck:
    """Test cases for backend health check function."""

    def test_health_check_success(self):
        """Test successful health check."""
        from requirements_advisor_client.frontend.app import check_backend_health

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "healthy",
            "mcp_connected": True,
        }

        with patch("requests.get", return_value=mock_response):
            result = check_backend_health()

            assert result["status"] == "healthy"
            assert result["mcp_connected"] is True

    def test_health_check_failure(self):
        """Test health check on connection failure."""
        from requirements_advisor_client.frontend.app import check_backend_health

        with patch("requests.get", side_effect=Exception("Connection refused")):
            result = check_backend_health()

            assert result["status"] == "unhealthy"
            assert result["mcp_connected"] is False


class TestGetAvailableTools:
    """Test cases for getting available tools."""

    def test_get_tools_success(self):
        """Test successful tool retrieval."""
        from requirements_advisor_client.frontend.app import get_available_tools

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"name": "tool1", "description": "Description 1"},
            {"name": "tool2", "description": "Description 2"},
        ]

        with patch("requests.get", return_value=mock_response):
            tools = get_available_tools()

            assert len(tools) == 2
            assert tools[0]["name"] == "tool1"

    def test_get_tools_failure(self):
        """Test tool retrieval on failure."""
        from requirements_advisor_client.frontend.app import get_available_tools

        with patch("requests.get", side_effect=Exception("Error")):
            tools = get_available_tools()

            assert tools == []

    def test_get_tools_non_200(self):
        """Test tool retrieval with non-200 response."""
        from requirements_advisor_client.frontend.app import get_available_tools

        mock_response = MagicMock()
        mock_response.status_code = 503

        with patch("requests.get", return_value=mock_response):
            tools = get_available_tools()

            assert tools == []


class TestSendChatMessage:
    """Test cases for sending chat messages."""

    def test_send_message_success(self):
        """Test successful message send."""
        from requirements_advisor_client.frontend.app import send_chat_message

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": "Test response",
            "session_id": "test-session",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_response):
            result = send_chat_message(
                message="Hello",
                session_id=None,
                provider="claude",
                history=[],
            )

            assert result["response"] == "Test response"
            assert result["session_id"] == "test-session"

    def test_send_message_timeout(self):
        """Test message send timeout."""
        from requirements_advisor_client.frontend.app import send_chat_message

        import requests

        with patch("requests.post", side_effect=requests.exceptions.Timeout):
            result = send_chat_message(
                message="Hello",
                session_id=None,
                provider="claude",
                history=[],
            )

            assert "error" in result
            assert "timeout" in result["error"].lower()

    def test_send_message_connection_error(self):
        """Test message send connection error."""
        from requirements_advisor_client.frontend.app import send_chat_message

        import requests

        with patch(
            "requests.post",
            side_effect=requests.exceptions.ConnectionError("Connection refused"),
        ):
            result = send_chat_message(
                message="Hello",
                session_id=None,
                provider="claude",
                history=[],
            )

            assert "error" in result
            assert "failed to connect" in result["error"].lower()


class TestStyles:
    """Test cases for styling functions."""

    def test_jama_brand_colors(self):
        """Test that Jama brand colors are defined."""
        from requirements_advisor_client.frontend.styles import (
            JAMA_ORANGE,
            JAMA_DARK,
            JAMA_TEXT,
        )

        assert JAMA_ORANGE == "#E86826"
        assert JAMA_DARK == "#1A1A2E"
        assert JAMA_TEXT == "#333333"

    def test_apply_jama_branding(self):
        """Test that branding function calls st.markdown."""
        from requirements_advisor_client.frontend.styles import apply_jama_branding

        mock_st = MagicMock()

        with patch(
            "requirements_advisor_client.frontend.styles.st",
            mock_st,
        ):
            apply_jama_branding()

            mock_st.markdown.assert_called_once()
            call_args = mock_st.markdown.call_args
            assert "E86826" in call_args[0][0]  # Jama orange
            assert call_args[1]["unsafe_allow_html"] is True

    def test_render_status_indicator_connected(self):
        """Test rendering connected status indicator."""
        from requirements_advisor_client.frontend.styles import render_status_indicator

        mock_st = MagicMock()

        with patch(
            "requirements_advisor_client.frontend.styles.st",
            mock_st,
        ):
            render_status_indicator(connected=True, label="Backend")

            mock_st.markdown.assert_called_once()
            call_args = mock_st.markdown.call_args
            assert "Connected" in call_args[0][0]
            assert "status-connected" in call_args[0][0]

    def test_render_status_indicator_disconnected(self):
        """Test rendering disconnected status indicator."""
        from requirements_advisor_client.frontend.styles import render_status_indicator

        mock_st = MagicMock()

        with patch(
            "requirements_advisor_client.frontend.styles.st",
            mock_st,
        ):
            render_status_indicator(connected=False, label="MCP Server")

            call_args = mock_st.markdown.call_args
            assert "Disconnected" in call_args[0][0]
            assert "status-disconnected" in call_args[0][0]
