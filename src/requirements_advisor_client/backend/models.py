"""
Pydantic models for API request/response schemas.

Defines the data structures used by the FastAPI endpoints.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request model for the chat endpoint.

    Attributes:
        message: The user's message to process.
        session_id: Optional session ID for conversation continuity.
        provider: LLM provider to use (claude, openai, gemini).
        history: Previous conversation messages for context.
    """

    message: str = Field(..., description="The user's message to process")
    session_id: str | None = Field(default=None, description="Session ID for conversation")
    provider: str = Field(default="claude", description="LLM provider (claude, openai, gemini)")
    history: list[dict] = Field(default_factory=list, description="Previous messages for context")


class ChatResponse(BaseModel):
    """Response model for the chat endpoint.

    Attributes:
        response: The assistant's response text.
        session_id: Session ID for the conversation.
        tools_used: List of MCP tools that were invoked.
    """

    response: str = Field(..., description="The assistant's response")
    session_id: str = Field(..., description="Session ID for the conversation")
    tools_used: list[str] = Field(default_factory=list, description="Tools that were invoked")


class ToolInfo(BaseModel):
    """Information about an available MCP tool.

    Attributes:
        name: The tool's unique identifier.
        description: Human-readable description of the tool's purpose.
    """

    name: str = Field(..., description="Tool identifier")
    description: str = Field(default="", description="Tool description")


class HealthResponse(BaseModel):
    """Response model for the health check endpoint.

    Attributes:
        status: Overall health status (healthy/unhealthy).
        mcp_connected: Whether the MCP server connection is active.
        version: Application version string.
    """

    status: str = Field(..., description="Health status")
    mcp_connected: bool = Field(..., description="MCP server connection status")
    version: str = Field(default="0.1.0", description="Application version")


class MessageRecord(BaseModel):
    """Model for a chat message record from the database.

    Attributes:
        role: Message role (user or assistant).
        content: Message content text.
        created_at: Timestamp when the message was created.
    """

    role: str = Field(..., description="Message role (user/assistant)")
    content: str = Field(..., description="Message content")
    created_at: datetime = Field(..., description="Creation timestamp")
