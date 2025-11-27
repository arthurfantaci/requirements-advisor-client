"""Tests for the MCP client module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestMCPClient:
    """Test cases for the MCPClient class."""

    def test_init(self):
        """Test MCPClient initialization."""
        from requirements_advisor_client.backend.mcp_client import MCPClient

        client = MCPClient()

        assert client.session is None
        assert client._tools_cache is None
        assert client._server_url is None
        assert client.is_connected is False
        assert client.server_url is None

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful connection to MCP server."""
        from requirements_advisor_client.backend.mcp_client import MCPClient

        mock_session = MagicMock()
        mock_session.initialize = AsyncMock()
        mock_tools = MagicMock()
        mock_tools.tools = [MagicMock(name="test_tool")]
        mock_session.list_tools = AsyncMock(return_value=mock_tools)

        with patch(
            "requirements_advisor_client.backend.mcp_client.streamablehttp_client"
        ) as mock_transport:
            mock_transport.return_value.__aenter__ = AsyncMock(
                return_value=(MagicMock(), MagicMock(), MagicMock())
            )
            mock_transport.return_value.__aexit__ = AsyncMock()

            with patch(
                "requirements_advisor_client.backend.mcp_client.ClientSession"
            ) as mock_client_session:
                mock_client_session.return_value.__aenter__ = AsyncMock(
                    return_value=mock_session
                )
                mock_client_session.return_value.__aexit__ = AsyncMock()

                client = MCPClient()
                await client.connect("https://test.example.com/mcp")

                assert client.is_connected
                assert client.server_url == "https://test.example.com/mcp"
                mock_session.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_with_headers(self):
        """Test connection with custom headers."""
        from requirements_advisor_client.backend.mcp_client import MCPClient

        mock_session = MagicMock()
        mock_session.initialize = AsyncMock()
        mock_session.list_tools = AsyncMock(return_value=MagicMock(tools=[]))

        with patch(
            "requirements_advisor_client.backend.mcp_client.streamablehttp_client"
        ) as mock_transport:
            mock_transport.return_value.__aenter__ = AsyncMock(
                return_value=(MagicMock(), MagicMock(), MagicMock())
            )
            mock_transport.return_value.__aexit__ = AsyncMock()

            with patch(
                "requirements_advisor_client.backend.mcp_client.ClientSession"
            ) as mock_client_session:
                mock_client_session.return_value.__aenter__ = AsyncMock(
                    return_value=mock_session
                )
                mock_client_session.return_value.__aexit__ = AsyncMock()

                client = MCPClient()
                await client.connect(
                    "https://test.example.com/mcp",
                    headers={"Authorization": "Bearer token"},
                )

                mock_transport.assert_called_with(
                    "https://test.example.com/mcp",
                    headers={"Authorization": "Bearer token"},
                )

    @pytest.mark.asyncio
    async def test_list_tools_not_connected(self):
        """Test listing tools when not connected returns empty list."""
        from requirements_advisor_client.backend.mcp_client import MCPClient

        client = MCPClient()
        tools = await client.list_tools()

        assert tools == []

    @pytest.mark.asyncio
    async def test_list_tools_connected(self, mock_mcp_client):
        """Test listing tools when connected."""
        tools = await mock_mcp_client.list_tools()

        assert len(tools) == 1
        assert tools[0].name == "search_requirements"

    @pytest.mark.asyncio
    async def test_call_tool_not_connected(self):
        """Test calling tool when not connected raises error."""
        from requirements_advisor_client.backend.mcp_client import MCPClient

        client = MCPClient()

        with pytest.raises(RuntimeError, match="Not connected"):
            await client.call_tool("test_tool", {"arg": "value"})

    @pytest.mark.asyncio
    async def test_call_tool_success(self, mock_mcp_client):
        """Test successful tool call."""
        result = await mock_mcp_client.call_tool(
            "search_requirements",
            {"query": "test"},
        )

        assert result.content[0].text == "Test search result content"
        mock_mcp_client.call_tool.assert_called_with(
            "search_requirements",
            {"query": "test"},
        )

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Test disconnection clears state."""
        from requirements_advisor_client.backend.mcp_client import MCPClient

        client = MCPClient()
        client.session = MagicMock()
        client._tools_cache = MagicMock()
        client._server_url = "https://test.example.com/mcp"

        await client.disconnect()

        assert client.session is None
        assert client._tools_cache is None
        assert client._server_url is None
        assert client.is_connected is False
