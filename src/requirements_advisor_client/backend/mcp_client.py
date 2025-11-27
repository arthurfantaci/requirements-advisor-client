"""
MCP Client for connecting to remote MCP servers.

Provides async connection management and tool execution
using the official MCP Python SDK with Streamable HTTP transport.
"""

from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from requirements_advisor_client.backend.logging import get_logger

logger = get_logger("mcp_client")


class MCPClient:
    """Client for connecting to remote MCP servers.

    Manages the connection lifecycle and provides methods to list
    and execute tools on the connected MCP server.

    Attributes:
        session: The active MCP client session.
        _tools_cache: Cached list of available tools.

    Example:
        >>> client = MCPClient()
        >>> await client.connect("https://server.example.com/mcp")
        >>> tools = await client.list_tools()
        >>> result = await client.call_tool("search", {"query": "test"})
        >>> await client.disconnect()
    """

    def __init__(self) -> None:
        """Initialize the MCP client."""
        self.session: ClientSession | None = None
        self._exit_stack = AsyncExitStack()
        self._tools_cache = None
        self._server_url: str | None = None

    @property
    def is_connected(self) -> bool:
        """Check if the client is connected to an MCP server.

        Returns:
            True if connected and session is active, False otherwise.
        """
        return self.session is not None

    @property
    def server_url(self) -> str | None:
        """Get the URL of the connected MCP server.

        Returns:
            The server URL if connected, None otherwise.
        """
        return self._server_url if self.is_connected else None

    async def connect(
        self,
        server_url: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Connect to a remote MCP server.

        Establishes a connection using Streamable HTTP transport,
        initializes the session, and caches available tools.

        Args:
            server_url: The URL of the MCP server endpoint (e.g., https://server/mcp).
            headers: Optional HTTP headers to include in requests.

        Raises:
            Exception: If connection or initialization fails.

        Example:
            >>> await client.connect(
            ...     "https://my-mcp-server.railway.app/mcp",
            ...     headers={"Authorization": "Bearer token"}
            ... )
        """
        headers = headers or {}
        logger.info("Connecting to MCP server", url=server_url)

        try:
            streams = await self._exit_stack.enter_async_context(
                streamablehttp_client(server_url, headers=headers)
            )
            read, write, _ = streams

            self.session = await self._exit_stack.enter_async_context(
                ClientSession(read, write)
            )

            # Critical: always initialize the session
            await self.session.initialize()

            # Cache tools for performance
            self._tools_cache = await self.session.list_tools()
            self._server_url = server_url

            tool_count = len(self._tools_cache.tools) if self._tools_cache else 0
            logger.info("Connected to MCP server", tools_available=tool_count)

        except Exception as e:
            logger.error("Failed to connect to MCP server", error=str(e))
            raise

    async def list_tools(self) -> list:
        """Get the list of available tools from the MCP server.

        Returns cached tools if available.

        Returns:
            List of Tool objects with name, description, and inputSchema.

        Raises:
            RuntimeError: If not connected to an MCP server.
        """
        if not self.is_connected:
            logger.warning("Attempted to list tools without connection")
            return []

        return self._tools_cache.tools if self._tools_cache else []

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Execute a tool on the MCP server.

        Args:
            tool_name: The name of the tool to execute.
            arguments: Dictionary of arguments to pass to the tool.

        Returns:
            The tool execution result from the MCP server.

        Raises:
            RuntimeError: If not connected to an MCP server.
            Exception: If tool execution fails on the server.

        Example:
            >>> result = await client.call_tool(
            ...     "search_requirements",
            ...     {"query": "traceability", "top_k": 5}
            ... )
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to MCP server")

        logger.debug("Calling tool", tool=tool_name, arguments=arguments)

        try:
            result = await self.session.call_tool(tool_name, arguments)
            logger.debug("Tool call completed", tool=tool_name)
            return result
        except Exception as e:
            logger.error("Tool call failed", tool=tool_name, error=str(e))
            raise

    async def disconnect(self) -> None:
        """Disconnect from the MCP server.

        Cleans up resources and closes the connection.
        Safe to call multiple times.
        """
        if self.is_connected:
            logger.info("Disconnecting from MCP server")

        await self._exit_stack.aclose()
        self.session = None
        self._tools_cache = None
        self._server_url = None

    async def refresh_tools(self) -> list:
        """Refresh the cached list of tools from the server.

        Useful if tools may have been added or modified on the server.

        Returns:
            Updated list of Tool objects.
        """
        if not self.is_connected:
            return []

        self._tools_cache = await self.session.list_tools()
        logger.debug("Refreshed tools cache", count=len(self._tools_cache.tools))
        return self._tools_cache.tools if self._tools_cache else []
