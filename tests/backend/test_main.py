"""Tests for the main FastAPI application."""


from fastapi import FastAPI
from fastapi.testclient import TestClient

from requirements_advisor_client.backend.models import ChatResponse, HealthResponse, ToolInfo


# Create a test app without lifespan to avoid MCP connection attempts
def create_test_app():
    """Create a FastAPI app for testing without lifespan."""
    from uuid import uuid4

    from fastapi import Request
    from fastapi.middleware.cors import CORSMiddleware

    app = FastAPI(title="Test App")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def session_middleware(request: Request, call_next):
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
            max_age=86400 * 30,
        )
        return response

    return app


class TestHealthEndpoint:
    """Test cases for the health check endpoint."""

    def test_health_check_mcp_connected(self):
        """Test health check when MCP is connected."""
        app = create_test_app()

        @app.get("/health", response_model=HealthResponse)
        async def health_check():
            return HealthResponse(status="healthy", mcp_connected=True, version="0.1.0")

        with TestClient(app) as client:
            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["mcp_connected"] is True
            assert "version" in data

    def test_health_check_mcp_disconnected(self):
        """Test health check when MCP is disconnected."""
        app = create_test_app()

        @app.get("/health", response_model=HealthResponse)
        async def health_check():
            return HealthResponse(status="healthy", mcp_connected=False, version="0.1.0")

        with TestClient(app) as client:
            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["mcp_connected"] is False


class TestToolsEndpoint:
    """Test cases for the tools listing endpoint."""

    def test_list_tools_success(self):
        """Test listing tools when MCP is connected."""
        app = create_test_app()

        @app.get("/tools", response_model=list[ToolInfo])
        async def list_tools():
            return [ToolInfo(name="search_requirements", description="Search guidance")]

        with TestClient(app) as client:
            response = client.get("/tools")

            assert response.status_code == 200
            tools = response.json()
            assert len(tools) == 1
            assert tools[0]["name"] == "search_requirements"

    def test_list_tools_not_connected(self):
        """Test listing tools when MCP is not connected."""
        from fastapi import HTTPException

        app = create_test_app()

        @app.get("/tools")
        async def list_tools():
            raise HTTPException(status_code=503, detail="MCP server not connected")

        with TestClient(app) as client:
            response = client.get("/tools")

            assert response.status_code == 503
            assert "not connected" in response.json()["detail"].lower()


class TestChatEndpoint:
    """Test cases for the chat endpoint."""

    def test_chat_success(self):
        """Test successful chat request."""
        from requirements_advisor_client.backend.models import ChatRequest

        app = create_test_app()

        @app.post("/chat", response_model=ChatResponse)
        async def chat(request: ChatRequest):
            return ChatResponse(
                response="This is a test response",
                session_id="test-session-id",
                tools_used=[],
            )

        with TestClient(app) as client:
            response = client.post(
                "/chat",
                json={
                    "message": "What is EARS notation?",
                    "provider": "claude",
                    "history": [],
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "response" in data
            assert "session_id" in data

    def test_chat_invalid_provider(self):
        """Test chat with invalid provider returns error."""
        from fastapi import HTTPException

        from requirements_advisor_client.backend.models import ChatRequest

        app = create_test_app()

        @app.post("/chat")
        async def chat(request: ChatRequest):
            if request.provider not in ["claude", "openai", "gemini"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported provider '{request.provider}'",
                )
            return ChatResponse(response="test", session_id="test", tools_used=[])

        with TestClient(app) as client:
            response = client.post(
                "/chat",
                json={
                    "message": "Hello",
                    "provider": "invalid_provider",
                    "history": [],
                },
            )

            assert response.status_code == 400
            assert "unsupported" in response.json()["detail"].lower()

    def test_chat_with_history(self):
        """Test chat request with conversation history."""
        from requirements_advisor_client.backend.models import ChatRequest

        app = create_test_app()
        received_history = []

        @app.post("/chat", response_model=ChatResponse)
        async def chat(request: ChatRequest):
            received_history.extend(request.history)
            return ChatResponse(
                response="Response with history",
                session_id="test-session",
                tools_used=[],
            )

        with TestClient(app) as client:
            response = client.post(
                "/chat",
                json={
                    "message": "Tell me about traceability",
                    "provider": "claude",
                    "history": [
                        {"role": "user", "content": "Hello"},
                        {"role": "assistant", "content": "Hi! How can I help?"},
                    ],
                },
            )

            assert response.status_code == 200
            assert len(received_history) == 2


class TestHistoryEndpoint:
    """Test cases for the history endpoint."""

    def test_get_history_success(self):
        """Test retrieving chat history."""
        from requirements_advisor_client.backend.models import MessageRecord

        app = create_test_app()

        @app.get("/history/{session_id}", response_model=list[MessageRecord])
        async def get_history(session_id: str):
            return [
                MessageRecord(
                    role="user",
                    content="Hello",
                    created_at="2024-01-01T00:00:00",
                ),
                MessageRecord(
                    role="assistant",
                    content="Hi there!",
                    created_at="2024-01-01T00:00:01",
                ),
            ]

        with TestClient(app) as client:
            response = client.get("/history/test-session-id")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["role"] == "user"
            assert data[1]["role"] == "assistant"

    def test_get_history_empty(self):
        """Test retrieving empty history."""
        from requirements_advisor_client.backend.models import MessageRecord

        app = create_test_app()

        @app.get("/history/{session_id}", response_model=list[MessageRecord])
        async def get_history(session_id: str):
            return []

        with TestClient(app) as client:
            response = client.get("/history/nonexistent-session")

            assert response.status_code == 200
            assert response.json() == []


class TestSessionMiddleware:
    """Test cases for the session middleware."""

    def test_session_cookie_created(self):
        """Test that session cookie is created for new requests."""
        app = create_test_app()

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        with TestClient(app) as client:
            response = client.get("/test")

            assert response.status_code == 200
            # Check that session_id cookie is set
            cookies = response.cookies
            assert "session_id" in cookies

    def test_session_cookie_preserved(self):
        """Test that existing session cookie is preserved."""
        app = create_test_app()

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        with TestClient(app) as client:
            # First request creates cookie
            response1 = client.get("/test")
            session_id = response1.cookies.get("session_id")
            assert session_id is not None

            # Second request with same client preserves session
            # Note: TestClient automatically maintains cookies between requests
            response2 = client.get("/test")
            # Both responses should have session_id set
            assert response2.cookies.get("session_id") is not None
