"""Tests for the LLM integration module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestMCPToLiteLLMTools:
    """Test cases for MCP to LiteLLM tool conversion."""

    def test_convert_single_tool(self):
        """Test converting a single MCP tool to LiteLLM format."""
        from requirements_advisor_client.backend.llm import mcp_to_litellm_tools

        mock_tool = MagicMock()
        mock_tool.name = "search_requirements"
        mock_tool.description = "Search for requirements guidance"
        mock_tool.inputSchema = {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
            },
            "required": ["query"],
        }

        result = mcp_to_litellm_tools([mock_tool])

        assert len(result) == 1
        assert result[0]["type"] == "function"
        assert result[0]["function"]["name"] == "search_requirements"
        assert result[0]["function"]["description"] == "Search for requirements guidance"
        assert result[0]["function"]["parameters"] == mock_tool.inputSchema

    def test_convert_multiple_tools(self):
        """Test converting multiple MCP tools."""
        from requirements_advisor_client.backend.llm import mcp_to_litellm_tools

        tools = []
        for i in range(3):
            mock_tool = MagicMock()
            mock_tool.name = f"tool_{i}"
            mock_tool.description = f"Description {i}"
            mock_tool.inputSchema = {"type": "object"}
            tools.append(mock_tool)

        result = mcp_to_litellm_tools(tools)

        assert len(result) == 3
        for i, tool in enumerate(result):
            assert tool["function"]["name"] == f"tool_{i}"

    def test_convert_tool_without_description(self):
        """Test converting tool with no description."""
        from requirements_advisor_client.backend.llm import mcp_to_litellm_tools

        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        mock_tool.description = None
        mock_tool.inputSchema = {}

        result = mcp_to_litellm_tools([mock_tool])

        assert result[0]["function"]["description"] == ""

    def test_convert_empty_list(self):
        """Test converting empty tool list."""
        from requirements_advisor_client.backend.llm import mcp_to_litellm_tools

        result = mcp_to_litellm_tools([])

        assert result == []


class TestExtractToolResult:
    """Test cases for tool result extraction."""

    def test_extract_from_content_blocks(self):
        """Test extracting text from content blocks."""
        from requirements_advisor_client.backend.llm import extract_tool_result

        mock_result = MagicMock()
        mock_content1 = MagicMock()
        mock_content1.text = "First block"
        mock_content2 = MagicMock()
        mock_content2.text = "Second block"
        mock_result.content = [mock_content1, mock_content2]

        result = extract_tool_result(mock_result)

        assert result == "First block\nSecond block"

    def test_extract_from_string(self):
        """Test extracting from simple string result."""
        from requirements_advisor_client.backend.llm import extract_tool_result

        result = extract_tool_result("Simple string result")

        assert result == "Simple string result"

    def test_extract_from_object_without_content(self):
        """Test extracting from object without content attribute."""
        from requirements_advisor_client.backend.llm import extract_tool_result

        # Use a simple object without content attribute
        class SimpleResult:
            def __str__(self):
                return "String representation"

        mock_result = SimpleResult()
        result = extract_tool_result(mock_result)

        assert result == "String representation"


class TestCallLLMWithMCPTools:
    """Test cases for LLM calling with MCP tools."""

    @pytest.mark.asyncio
    async def test_call_without_tools(self, mock_litellm_response):
        """Test LLM call without any tools."""
        from requirements_advisor_client.backend.llm import call_llm_with_mcp_tools

        with patch("requirements_advisor_client.backend.llm.litellm") as mock_litellm:
            mock_litellm.completion.return_value = mock_litellm_response

            result = await call_llm_with_mcp_tools(
                provider="claude",
                messages=[{"role": "user", "content": "Hello"}],
                tools=[],
                mcp_client=None,
            )

            assert result == "This is a test response from the LLM."

    @pytest.mark.asyncio
    async def test_call_with_tool_execution(
        self,
        mock_mcp_client,
        mock_litellm_tool_call_response,
        mock_litellm_response,
    ):
        """Test LLM call that triggers tool execution."""
        from requirements_advisor_client.backend.llm import call_llm_with_mcp_tools

        with patch("requirements_advisor_client.backend.llm.litellm") as mock_litellm:
            # First call returns tool call, second returns final response
            mock_litellm.completion.side_effect = [
                mock_litellm_tool_call_response,
                mock_litellm_response,
            ]

            result = await call_llm_with_mcp_tools(
                provider="claude",
                messages=[{"role": "user", "content": "Search for test"}],
                tools=[{"type": "function", "function": {"name": "search"}}],
                mcp_client=mock_mcp_client,
            )

            assert result == "This is a test response from the LLM."
            mock_mcp_client.call_tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_unsupported_provider(self):
        """Test that unsupported provider raises ValueError."""
        from requirements_advisor_client.backend.llm import call_llm_with_mcp_tools

        with pytest.raises(ValueError, match="Unsupported provider"):
            await call_llm_with_mcp_tools(
                provider="unsupported",
                messages=[],
                tools=[],
                mcp_client=None,
            )

    @pytest.mark.asyncio
    async def test_max_iterations(self, mock_mcp_client, mock_litellm_tool_call_response):
        """Test that max iterations limit is respected."""
        from requirements_advisor_client.backend.llm import call_llm_with_mcp_tools

        with patch("requirements_advisor_client.backend.llm.litellm") as mock_litellm:
            # Always return tool calls to test iteration limit
            final_response = MagicMock()
            final_response.choices = [MagicMock()]
            final_response.choices[0].message.content = "Final response"
            final_response.choices[0].message.tool_calls = None

            mock_litellm.completion.side_effect = [
                mock_litellm_tool_call_response,
                mock_litellm_tool_call_response,
                final_response,
            ]

            result = await call_llm_with_mcp_tools(
                provider="claude",
                messages=[{"role": "user", "content": "Test"}],
                tools=[{"type": "function", "function": {"name": "search"}}],
                mcp_client=mock_mcp_client,
                max_iterations=2,
            )

            assert result == "Final response"


class TestSupportedProviders:
    """Test cases for provider-related functions."""

    def test_get_supported_providers(self):
        """Test getting list of supported providers."""
        from requirements_advisor_client.backend.llm import get_supported_providers

        providers = get_supported_providers()

        assert "claude" in providers
        assert "openai" in providers
        assert "gemini" in providers

    def test_get_model_for_provider(self):
        """Test getting model for valid provider."""
        from requirements_advisor_client.backend.llm import get_model_for_provider

        assert "claude" in get_model_for_provider("claude")
        assert "gpt-4o" == get_model_for_provider("openai")
        assert "gemini" in get_model_for_provider("gemini")

    def test_get_model_for_invalid_provider(self):
        """Test getting model for invalid provider returns None."""
        from requirements_advisor_client.backend.llm import get_model_for_provider

        assert get_model_for_provider("invalid") is None
