"""
FastAPI backend for Requirements Advisor MCP Client.

Provides REST API endpoints for chat with MCP tool integration
and multi-LLM support via LiteLLM.
"""

import asyncio
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from requirements_advisor_client.backend.config import settings
from requirements_advisor_client.backend.database import (
    cleanup_expired_sessions,
    get_history,
    get_or_create_session,
    init_database,
    save_message,
)
from requirements_advisor_client.backend.llm import (
    SYSTEM_MESSAGE,
    call_llm_with_mcp_tools,
    mcp_to_litellm_tools,
)
from requirements_advisor_client.backend.logging import get_logger, setup_logging
from requirements_advisor_client.backend.mcp_client import MCPClient
from requirements_advisor_client.backend.models import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    MessageRecord,
    ToolInfo,
)

# Initialize logging
setup_logging(level=settings.log_level, json_output=settings.log_json)
logger = get_logger("main")

# Global MCP client instance
mcp_client: MCPClient | None = None


async def session_cleanup_task() -> None:
    """Background task to periodically clean up expired sessions.

    Runs daily to remove sessions inactive for more than 30 days.
    """
    while True:
        try:
            await cleanup_expired_sessions(days=30)
        except Exception as e:
            logger.error("Session cleanup failed", error=str(e))
        await asyncio.sleep(86400)  # Run daily


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown.

    Manages database initialization, MCP server connection,
    and background cleanup tasks.
    """
    global mcp_client

    logger.info("Starting Requirements Advisor Client")

    # Ensure data directory exists (property creates it as side effect)
    _ = settings.data_dir

    # Initialize database
    await init_database()

    # Connect to MCP server
    mcp_client = MCPClient()
    try:
        await mcp_client.connect(settings.mcp_server_url)
    except Exception as e:
        logger.warning("Could not connect to MCP server", error=str(e))
        mcp_client = None

    # Start background cleanup task
    cleanup_task = asyncio.create_task(session_cleanup_task())

    yield

    # Cleanup on shutdown
    logger.info("Shutting down Requirements Advisor Client")
    cleanup_task.cancel()
    if mcp_client:
        await mcp_client.disconnect()


# FastAPI application
app = FastAPI(
    title="Requirements Advisor Client",
    description="MCP Client for Requirements Management Guidance",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def session_middleware(request: Request, call_next):
    """Middleware to handle session cookies.

    Creates a new session ID if one doesn't exist in the request,
    and sets an HTTP-only cookie in the response.
    """
    session_id = request.cookies.get("session_id")

    if not session_id:
        session_id = str(uuid4())

    request.state.session_id = session_id
    response = await call_next(request)

    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=86400 * 30,  # 30 days
    )
    return response


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint.

    Returns:
        Health status including MCP server connection status.
    """
    return HealthResponse(
        status="healthy",
        mcp_connected=mcp_client is not None and mcp_client.is_connected,
        version="0.1.0",
    )


@app.get("/tools", response_model=list[ToolInfo])
async def list_tools() -> list[ToolInfo]:
    """List available MCP tools.

    Returns:
        List of tool information with names and descriptions.

    Raises:
        HTTPException: If MCP server is not connected.
    """
    if not mcp_client or not mcp_client.is_connected:
        raise HTTPException(status_code=503, detail="MCP server not connected")

    tools = await mcp_client.list_tools()
    return [ToolInfo(name=t.name, description=t.description or "") for t in tools]


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, req: Request) -> ChatResponse:
    """Chat endpoint with MCP tool support.

    Processes user messages, invokes LLM with available tools,
    and persists conversation history.

    Args:
        request: Chat request with message and context.
        req: FastAPI request for session access.

    Returns:
        Chat response with assistant message and session ID.

    Raises:
        HTTPException: If LLM processing fails.
    """
    session_id = request.session_id or req.state.session_id

    # Ensure session exists in database
    await get_or_create_session(session_id)

    # Build messages for LLM
    messages: list[dict] = [{"role": "system", "content": SYSTEM_MESSAGE}]

    # Add conversation history (last 10 messages)
    for msg in request.history[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": request.message})

    # Get available tools
    tools: list[dict] = []
    if mcp_client and mcp_client.is_connected:
        mcp_tools = await mcp_client.list_tools()
        tools = mcp_to_litellm_tools(mcp_tools)

    # Call LLM with tools
    try:
        response_text = await call_llm_with_mcp_tools(
            provider=request.provider,
            messages=messages,
            tools=tools,
            mcp_client=mcp_client,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("LLM call failed", error=str(e))
        error_msg = str(e)
        # Provide helpful error messages for common API errors
        if "quota" in error_msg.lower() or "insufficient_quota" in error_msg.lower():
            raise HTTPException(
                status_code=402,
                detail=f"API quota exceeded for {request.provider}. Please check your billing.",
            ) from None
        if "rate" in error_msg.lower() and "limit" in error_msg.lower():
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded for {request.provider}. Try again later.",
            ) from None
        if "invalid" in error_msg.lower() and "key" in error_msg.lower():
            raise HTTPException(
                status_code=401,
                detail=f"Invalid API key for {request.provider}. Check your configuration.",
            ) from None
        raise HTTPException(status_code=500, detail=f"LLM error: {error_msg}") from None

    # Save messages to database
    await save_message(session_id, "user", request.message)
    await save_message(session_id, "assistant", response_text)

    return ChatResponse(
        response=response_text,
        session_id=session_id,
        tools_used=[],
    )


@app.get("/history/{session_id}", response_model=list[MessageRecord])
async def get_chat_history(session_id: str) -> list[MessageRecord]:
    """Get chat history for a session.

    Args:
        session_id: The session ID to retrieve history for.

    Returns:
        List of messages in chronological order.
    """
    history = await get_history(session_id)
    return [
        MessageRecord(
            role=msg["role"],
            content=msg["content"],
            created_at=msg["created_at"],
        )
        for msg in history
    ]


def cli() -> None:
    """CLI entry point for running the backend server.

    Can be invoked via: requirements-advisor-backend
    """
    import uvicorn

    uvicorn.run(
        "requirements_advisor_client.backend.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=False,
    )


if __name__ == "__main__":
    cli()
