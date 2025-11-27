# Building a Production MCP Client Web Application: Complete Implementation Guide

A production-quality MCP Client connecting to a remote server with multi-LLM support, FastAPI + Streamlit architecture, and Railway deployment is achievable within a **4-day timeline** using well-documented patterns and proven approaches. The key to success lies in using separate services (Streamlit frontend calling FastAPI backend), the official MCP Python SDK with Streamable HTTP transport, and LiteLLM for unified multi-provider tool calling.

---

## MCP Python SDK client implementation unlocks remote server connectivity

The official MCP Python SDK (`mcp` package, version 1.22.0) provides everything needed to connect to a remote MCP Server deployed at a Railway URL. **Streamable HTTP transport** is the recommended approach for remote servers—it supersedes the legacy SSE transport as of the March 2025 MCP specification.

### Installation and core imports

```bash
pip install "mcp[cli]"
```

```python
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client  # Recommended for remote
from mcp.client.sse import sse_client                         # Legacy fallback
```

### Production-ready MCP client class

The critical pattern for remote MCP connections involves three steps: establish the transport connection, create a `ClientSession`, and **always call `session.initialize()`** before any tool operations:

```python
import asyncio
from contextlib import AsyncExitStack
from typing import Optional, Any
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self._tools_cache = None
    
    async def connect(self, server_url: str, headers: Optional[dict] = None):
        """Connect to remote MCP server (e.g., https://your-server.railway.app/mcp)"""
        headers = headers or {}
        streams = await self.exit_stack.enter_async_context(
            streamablehttp_client(server_url, headers=headers)
        )
        read, write, _ = streams
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(read, write)
        )
        await self.session.initialize()  # Critical: always call this
        self._tools_cache = await self.session.list_tools()
    
    async def list_tools(self) -> list:
        return self._tools_cache.tools if self._tools_cache else []
    
    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        return await self.session.call_tool(tool_name, arguments)
    
    async def disconnect(self):
        await self.exit_stack.aclose()
```

**Transport selection guidance**: If your MCP server URL ends with `/mcp`, use Streamable HTTP. If it ends with `/sse`, use the legacy SSE transport. For new Railway deployments, configure the server to expose a `/mcp` endpoint and use Streamable HTTP exclusively.

---

## Multi-LLM orchestration requires format normalization across providers

Claude, GPT-4, and Gemini all support tool/function calling but use **different schema formats and response structures**. The key differences that require normalization:

| Aspect | Claude | OpenAI | Gemini |
|--------|--------|--------|--------|
| Schema key | `input_schema` | `parameters` | `parameters` |
| Tool wrapper | Direct in `tools[]` | Nested in `tools[].function` | Nested in `functionDeclarations[]` |
| Arguments format | Python object | JSON string (needs parsing) | Python object |
| Tool call ID | `id` in tool_use block | `tool_call_id` | Name-based (no ID) |
| Result role | `user` with `tool_result` | `tool` | `user` with `functionResponse` |

### LiteLLM provides the fastest path to unified tool calling

For a 4-day timeline, **LiteLLM is the strongly recommended approach**—it normalizes tool calling across all three providers into a single OpenAI-compatible interface:

```python
import litellm
import json

# Universal tool definition works with all providers
tools = [{
    "type": "function",
    "function": {
        "name": "search_requirements",
        "description": "Search requirements in Jama Connect",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "project_id": {"type": "integer", "description": "Project ID"}
            },
            "required": ["query"]
        }
    }
}]

def call_llm_with_tools(provider: str, messages: list, tools: list):
    """Unified LLM call with tool support across providers"""
    model_map = {
        "claude": "anthropic/claude-sonnet-4-20250514",
        "openai": "gpt-4o",
        "gemini": "gemini/gemini-2.5-flash"
    }
    
    response = litellm.completion(
        model=model_map[provider],
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )
    
    # All providers return OpenAI-compatible format via LiteLLM
    if response.choices[0].message.tool_calls:
        for tool_call in response.choices[0].message.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            yield {"tool_call_id": tool_call.id, "name": name, "arguments": args}
    
    return response
```

### Converting MCP tools to LLM format

MCP tool schemas map directly to LLM tool definitions with minimal transformation:

```python
def mcp_to_litellm_tools(mcp_tools: list) -> list:
    """Convert MCP tool list to LiteLLM/OpenAI format"""
    return [{
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.inputSchema
        }
    } for tool in mcp_tools]
```

---

## Separate FastAPI and Streamlit services is the optimal architecture

For a 4-day timeline with production quality, **separate services with REST API communication** provides clear separation of concerns, independent scaling, and established deployment patterns. The architecture:

```
┌─────────────────────┐     REST API      ┌─────────────────────┐
│  Streamlit Frontend │ ←───────────────→ │   FastAPI Backend   │
│  (port 8501)        │                   │   (port 8000)       │
│  - Chat UI          │                   │   - MCP Client      │
│  - Session state    │                   │   - LLM Integration │
│  - Custom styling   │                   │   - Session storage │
└─────────────────────┘                   └─────────────────────┘
```

### Streamlit chat interface with session state

**Critical pattern**: Streamlit re-runs the entire script on every interaction. Always check if session state keys exist before initializing:

```python
import streamlit as st
import requests

API_URL = st.secrets.get("API_URL", "http://localhost:8000")

# Initialize session state ONCE at script start
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "selected_llm" not in st.session_state:
    st.session_state.selected_llm = "claude"

st.set_page_config(page_title="Requirements Assistant", layout="wide")
st.title("📋 Requirements Management Assistant")

# LLM selector in sidebar
with st.sidebar:
    st.session_state.selected_llm = st.selectbox(
        "Select AI Provider",
        ["claude", "openai", "gemini"],
        index=["claude", "openai", "gemini"].index(st.session_state.selected_llm)
    )
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# Display conversation history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask about requirements..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = requests.post(
                f"{API_URL}/chat",
                json={
                    "message": prompt,
                    "session_id": st.session_state.session_id,
                    "provider": st.session_state.selected_llm,
                    "history": st.session_state.messages[-10:]
                },
                timeout=60
            )
            data = response.json()
            st.session_state.session_id = data.get("session_id")
            st.markdown(data["response"])
            st.session_state.messages.append({
                "role": "assistant",
                "content": data["response"]
            })
```

### FastAPI backend structure

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import asyncio

app = FastAPI()

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    provider: str = "claude"
    history: List[dict] = []

class ChatResponse(BaseModel):
    response: str
    session_id: str
    tool_calls: List[dict] = []

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    # Create/retrieve session
    session_id = request.session_id or str(uuid4())
    
    # Connect to MCP server and get tools
    mcp_client = await get_mcp_client()
    tools = mcp_to_litellm_tools(await mcp_client.list_tools())
    
    # Call LLM with tools
    messages = [{"role": m["role"], "content": m["content"]} for m in request.history]
    messages.append({"role": "user", "content": request.message})
    
    response = await call_llm_with_mcp_tools(
        provider=request.provider,
        messages=messages,
        tools=tools,
        mcp_client=mcp_client
    )
    
    # Persist to database
    await save_message(session_id, "user", request.message)
    await save_message(session_id, "assistant", response)
    
    return ChatResponse(response=response, session_id=session_id)
```

---

## Railway deployment configuration for multi-service architecture

Railway excels at deploying multiple Python services that communicate via **private IPv6 networking**. The key configuration files and patterns:

### Project structure for Railway

```
mcp-client-app/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── requirements.txt
│   ├── railway.json
│   └── .python-version      # "3.11"
├── frontend/
│   ├── app.py               # Streamlit application
│   ├── requirements.txt
│   ├── railway.json
│   └── .streamlit/
│       └── config.toml      # Theme configuration
└── README.md
```

### Backend railway.json (FastAPI)

```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": {"builder": "NIXPACKS"},
  "deploy": {
    "startCommand": "uvicorn main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 300,
    "restartPolicyType": "ON_FAILURE"
  }
}
```

### Frontend railway.json (Streamlit)

```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": {"builder": "NIXPACKS"},
  "deploy": {
    "startCommand": "streamlit run app.py --server.address 0.0.0.0 --server.port $PORT --server.fileWatcherType none --browser.gatherUsageStats false"
  }
}
```

### Inter-service communication on Railway

Railway provides internal DNS for private networking. In the frontend service's environment variables:

```
API_URL=http://${{backend.RAILWAY_PRIVATE_DOMAIN}}:${{backend.PORT}}
```

**Important caveat**: Private networking uses IPv6. For internal-only services, bind to `[::]` instead of `0.0.0.0`.

### Database setup for session persistence

For **10-15 users**, Railway PostgreSQL is recommended over SQLite because Railway's ephemeral filesystem makes SQLite unreliable across deployments:

1. Add PostgreSQL via Railway dashboard: **+ New → Database → PostgreSQL**
2. Reference in backend environment variables:
```
DATABASE_URL=${{Postgres.DATABASE_URL}}
```

**Estimated costs** (Hobby Plan $5/month with $5 usage credit):
- FastAPI backend: ~$1-2/month
- Streamlit frontend: ~$2-3/month  
- PostgreSQL: ~$1/month
- **Total**: ~$5-7/month for 10-15 light users

---

## Anonymous session persistence uses UUID cookies with server-side storage

The recommended pattern combines **HTTP-only cookies for session identification** with PostgreSQL for chat history persistence:

### Session middleware for FastAPI

```python
from fastapi import FastAPI, Request, Response
from uuid import uuid4

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
        httponly=True,      # Prevents XSS attacks
        secure=True,        # HTTPS only in production
        samesite="lax",     # CSRF protection
        max_age=86400 * 30  # 30 days
    )
    return response
```

### Database schema for chat history

```python
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

class Session(Base):
    __tablename__ = "sessions"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    role = Column(String(20))  # "user" or "assistant"
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    session = relationship("Session", back_populates="messages")
```

### Session cleanup background task

```python
import asyncio
from datetime import datetime, timedelta

async def cleanup_expired_sessions():
    while True:
        cutoff = datetime.utcnow() - timedelta(days=30)
        async with get_db() as db:
            await db.execute(
                "DELETE FROM sessions WHERE last_activity < :cutoff",
                {"cutoff": cutoff}
            )
            await db.commit()
        await asyncio.sleep(86400)  # Run daily

@app.on_event("startup")
async def start_cleanup():
    asyncio.create_task(cleanup_expired_sessions())
```

---

## Jama Software branding emphasizes signature orange with professional B2B aesthetics

Based on Jama Software's 2019 rebrand (executed by Murmur Creative), the brand identity centers on **signature orange** representing innovation and warmth, combined with clean professional typography typical of enterprise B2B SaaS products.

### Brand color implementation

The primary brand color is a **warm orange** (#E86826 or similar), used for CTAs, highlights, and accent elements. Secondary colors include professional grays and blues for text and backgrounds. The visual identity emphasizes:

- **Primary accent**: Warm orange for buttons, links, and highlights
- **Text colors**: Dark gray/charcoal for body text, maintaining high contrast
- **Backgrounds**: Clean whites and light grays for professional readability
- **Secondary accent**: Complementary blues for informational elements

### Streamlit custom CSS for Jama-inspired branding

Create `.streamlit/config.toml`:

```toml
[theme]
base = "light"
primaryColor = "#E86826"           # Jama signature orange
backgroundColor = "#FFFFFF"         # Clean white background
secondaryBackgroundColor = "#F5F5F5"
textColor = "#333333"
font = "sans serif"
```

For deeper customization, inject CSS via `st.markdown`:

```python
def apply_jama_branding():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        /* Global typography */
        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        
        /* Primary buttons - Jama orange */
        .stButton > button {
            background-color: #E86826;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 10px 24px;
            font-weight: 600;
            transition: background-color 0.2s ease;
        }
        
        .stButton > button:hover {
            background-color: #D45A1F;
        }
        
        /* Chat messages */
        div[data-testid="stChatMessageContent"] {
            background-color: #F8F9FA;
            border-radius: 12px;
            padding: 16px;
            border: 1px solid #E5E7EB;
        }
        
        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background-color: #1A1A2E;
        }
        
        [data-testid="stSidebar"] .stMarkdown {
            color: #E5E7EB;
        }
        
        /* Chat input */
        .stChatInput > div {
            border: 2px solid #E5E7EB;
            border-radius: 24px;
        }
        
        .stChatInput > div:focus-within {
            border-color: #E86826;
        }
        
        /* Headers */
        h1 { color: #1A1A2E; font-weight: 700; }
        h2, h3 { color: #333333; font-weight: 600; }
        
        /* Hide Streamlit branding for professional appearance */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

# Call at app start
apply_jama_branding()
```

---

## Four-day implementation timeline prioritizes proven patterns

### Day 1: Backend foundation
- Set up FastAPI project structure with health endpoint
- Implement MCP client connection to remote server
- Integrate LiteLLM for multi-provider support
- Create `/chat` endpoint with basic tool calling loop

### Day 2: Frontend and integration  
- Build Streamlit chat interface with `st.chat_message` and `st.chat_input`
- Implement session state management for conversation history
- Add LLM provider selector in sidebar
- Connect frontend to backend API

### Day 3: Persistence and styling
- Set up PostgreSQL on Railway
- Implement anonymous session middleware with UUID cookies
- Add chat history persistence and retrieval
- Apply Jama-inspired CSS branding and theming

### Day 4: Deployment and polish
- Configure `railway.json` for both services
- Deploy to Railway with environment variables
- Set up inter-service communication via private networking
- Test end-to-end flow, add error handling, generate custom domain

---

## Conclusion

Building a production MCP Client with multi-LLM support is achievable in 4 days by leveraging: the official MCP Python SDK with Streamable HTTP transport for remote server connectivity; LiteLLM for unified tool calling across Claude, GPT-4, and Gemini; separate FastAPI/Streamlit services for clean architecture; Railway's multi-service deployment with PostgreSQL for persistence; and UUID-based anonymous sessions with HTTP-only cookies. The combination of Jama's signature orange accent color with Inter typography creates a professional, branded interface that maintains enterprise credibility while delivering a modern chat experience.