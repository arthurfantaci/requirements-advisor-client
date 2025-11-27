"""
LLM integration using LiteLLM for multi-provider support.

Provides unified tool calling across Claude, GPT-4, and Gemini
with automatic format conversion from MCP tool schemas.
"""

import asyncio
import json
from typing import Any

import litellm

from requirements_advisor_client.backend.logging import get_logger
from requirements_advisor_client.backend.mcp_client import MCPClient

logger = get_logger("llm")

# Model mapping for supported providers
MODEL_MAP: dict[str, str] = {
    "claude": "anthropic/claude-sonnet-4-20250514",
    "openai": "gpt-4o",
    "gemini": "gemini/gemini-2.5-flash",
}

# System message for the requirements advisor
SYSTEM_MESSAGE = (
    "You are a helpful assistant specializing in requirements management. "
    "You have access to tools that can search authoritative sources about "
    "requirements management best practices, including guidance from Jama Software, "
    "INCOSE, and EARS notation. Use these tools to provide accurate, well-sourced answers."
)


def mcp_to_litellm_tools(mcp_tools: list) -> list[dict[str, Any]]:
    """Convert MCP tool schemas to LiteLLM/OpenAI format.

    Args:
        mcp_tools: List of MCP Tool objects with name, description, and inputSchema.

    Returns:
        List of tool definitions in OpenAI function calling format.

    Example:
        >>> tools = await mcp_client.list_tools()
        >>> litellm_tools = mcp_to_litellm_tools(tools)
    """
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.inputSchema,
            },
        }
        for tool in mcp_tools
    ]


def extract_tool_result(result: Any) -> str:
    """Extract text content from an MCP tool result.

    Handles both structured results with content blocks and
    simple string results.

    Args:
        result: The result from an MCP tool call.

    Returns:
        Extracted text content as a string.
    """
    if hasattr(result, "content"):
        return "\n".join(c.text for c in result.content if hasattr(c, "text"))
    return str(result)


async def call_llm_with_mcp_tools(
    provider: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    mcp_client: MCPClient | None,
    max_iterations: int = 5,
) -> str:
    """Call an LLM with MCP tool support and handle the tool execution loop.

    Sends messages to the specified LLM provider, executes any requested
    tool calls via the MCP client, and continues until the LLM provides
    a final response or max iterations is reached.

    Args:
        provider: LLM provider key (claude, openai, gemini).
        messages: Conversation messages including system message.
        tools: List of available tools in LiteLLM format.
        mcp_client: Connected MCP client for tool execution.
        max_iterations: Maximum tool calling iterations (default: 5).

    Returns:
        The final response text from the LLM.

    Raises:
        ValueError: If an unsupported provider is specified.
        Exception: If LLM API calls fail.

    Example:
        >>> response = await call_llm_with_mcp_tools(
        ...     provider="claude",
        ...     messages=[{"role": "user", "content": "What is EARS notation?"}],
        ...     tools=litellm_tools,
        ...     mcp_client=mcp_client,
        ... )
    """
    model = MODEL_MAP.get(provider)
    if not model:
        available = ", ".join(MODEL_MAP.keys())
        raise ValueError(f"Unsupported provider '{provider}'. Available: {available}")

    logger.info("Starting LLM call", provider=provider, model=model)
    current_messages = messages.copy()

    for iteration in range(max_iterations):
        logger.debug("LLM iteration", iteration=iteration + 1, max=max_iterations)

        # Call the LLM (run in thread to avoid blocking)
        response = await asyncio.to_thread(
            litellm.completion,
            model=model,
            messages=current_messages,
            tools=tools if tools else None,
            tool_choice="auto" if tools else None,
        )

        assistant_message = response.choices[0].message

        # If no tool calls, return the response
        if not assistant_message.tool_calls:
            logger.info("LLM completed", iterations=iteration + 1)
            return assistant_message.content or ""

        # Add assistant message with tool calls to history
        current_messages.append(assistant_message.model_dump())

        # Execute each tool call
        for tool_call in assistant_message.tool_calls:
            tool_name = tool_call.function.name
            logger.debug("Executing tool", tool=tool_name)

            # Parse arguments
            try:
                tool_args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                logger.warning("Failed to parse tool arguments", tool=tool_name)
                tool_args = {}

            # Execute tool via MCP client
            if mcp_client and mcp_client.is_connected:
                try:
                    result = await mcp_client.call_tool(tool_name, tool_args)
                    tool_result = extract_tool_result(result)
                except Exception as e:
                    logger.error("Tool execution failed", tool=tool_name, error=str(e))
                    tool_result = f"Error calling tool: {e}"
            else:
                tool_result = "Error: MCP client not connected"

            # Add tool result to messages
            current_messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_result,
            })

    # Max iterations reached - get final response without tools
    logger.warning("Max iterations reached, getting final response")
    final_response = await asyncio.to_thread(
        litellm.completion,
        model=model,
        messages=current_messages,
    )
    return final_response.choices[0].message.content or ""


def get_supported_providers() -> list[str]:
    """Get list of supported LLM providers.

    Returns:
        List of provider keys that can be used with call_llm_with_mcp_tools.
    """
    return list(MODEL_MAP.keys())


def get_model_for_provider(provider: str) -> str | None:
    """Get the model identifier for a provider.

    Args:
        provider: Provider key (claude, openai, gemini).

    Returns:
        Model identifier string or None if provider not found.
    """
    return MODEL_MAP.get(provider)
