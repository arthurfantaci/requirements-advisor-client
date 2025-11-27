"""
Streamlit frontend for Requirements Advisor MCP Client.

Provides a chat interface with multi-LLM support and Jama-inspired branding.
"""

import requests
import streamlit as st

from requirements_advisor_client.frontend.config import frontend_settings
from requirements_advisor_client.frontend.styles import (
    apply_jama_branding,
    render_guardrail_indicator,
    render_status_indicator,
)


def check_backend_health() -> dict:
    """Check if the backend is healthy and MCP is connected.

    Returns:
        Dictionary with status and mcp_connected keys.
        Returns unhealthy status on connection failure.
    """
    try:
        response = requests.get(f"{frontend_settings.api_url}/health", timeout=5)
        return response.json()
    except Exception:
        return {"status": "unhealthy", "mcp_connected": False}


def get_available_tools() -> list[dict]:
    """Get list of available MCP tools from the backend.

    Returns:
        List of tool dictionaries with name and description.
        Returns empty list on error.
    """
    try:
        response = requests.get(f"{frontend_settings.api_url}/tools", timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return []


def send_chat_message(
    message: str,
    session_id: str | None,
    provider: str,
    history: list[dict],
) -> dict:
    """Send a chat message to the backend API.

    Args:
        message: The user's message to send.
        session_id: Optional session ID for conversation continuity.
        provider: LLM provider to use (claude, openai, gemini).
        history: Previous conversation messages for context.

    Returns:
        Response dictionary with keys:
        - 'response': The assistant's response text
        - 'session_id': Session ID for conversation continuity
        - 'was_redirected': True if off-topic redirect occurred
        - 'content_filtered': True if output was filtered for safety
        - 'error': Error message on failure (mutually exclusive with above)
    """
    try:
        response = requests.post(
            f"{frontend_settings.api_url}/chat",
            json={
                "message": message,
                "session_id": session_id,
                "provider": provider,
                "history": history,
            },
            timeout=120,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        return {"error": "Request timed out. Please try again."}
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to connect to server: {e}"}


def render_sidebar() -> None:
    """Render the sidebar with controls and status information."""
    with st.sidebar:
        st.markdown("### Requirements Advisor")
        st.markdown("*Expert guidance on requirements management*")
        st.markdown("---")

        # LLM provider selector
        st.markdown("**AI Provider**")
        provider_options = {
            "claude": "Claude (Anthropic)",
            "openai": "GPT-4o (OpenAI)",
            "gemini": "Gemini (Google)",
        }
        st.session_state.selected_llm = st.selectbox(
            "Select AI Provider",
            options=list(provider_options.keys()),
            format_func=lambda x: provider_options[x],
            index=list(provider_options.keys()).index(st.session_state.selected_llm),
            label_visibility="collapsed",
        )

        st.markdown("---")

        # Backend status
        st.markdown("**Status**")
        health = check_backend_health()

        render_status_indicator(
            connected=health.get("status") == "healthy",
            label="Backend",
        )

        if health.get("status") == "healthy":
            render_status_indicator(
                connected=health.get("mcp_connected", False),
                label="MCP Server",
            )

        st.markdown("---")

        # Available tools
        if health.get("mcp_connected"):
            with st.expander("Available Tools", expanded=False):
                tools = get_available_tools()
                if tools:
                    for tool in tools:
                        st.markdown(f"**{tool['name']}**")
                        description = tool.get("description", "")
                        if len(description) > 100:
                            description = description[:100] + "..."
                        st.markdown(
                            f"<small>{description}</small>",
                            unsafe_allow_html=True,
                        )
                        st.markdown("---")
                else:
                    st.markdown("*No tools available*")

        st.markdown("---")

        # Clear chat button
        if st.button("Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.session_id = None
            st.rerun()

        # Footer
        st.markdown("---")
        st.markdown(
            "<small>Powered by MCP + LiteLLM</small>",
            unsafe_allow_html=True,
        )


def render_chat() -> None:
    """Render the main chat interface."""
    st.title("Requirements Advisor")
    st.markdown(
        "Ask questions about requirements management best practices, "
        "INCOSE guidelines, EARS notation, and more."
    )

    # Display conversation history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask about requirements management..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get assistant response
        with st.chat_message("assistant"), st.spinner("Thinking..."):
            result = send_chat_message(
                message=prompt,
                session_id=st.session_state.session_id,
                provider=st.session_state.selected_llm,
                history=st.session_state.messages[-10:],
            )

            if "error" in result:
                response_text = f"*Error: {result['error']}*"
                was_redirected = False
                content_filtered = False
            else:
                response_text = result.get("response", "No response received.")
                st.session_state.session_id = result.get("session_id")
                was_redirected = result.get("was_redirected", False)
                content_filtered = result.get("content_filtered", False)

            st.markdown(response_text)

            # Render subtle guardrail indicators
            if was_redirected:
                render_guardrail_indicator("redirected")
            if content_filtered:
                render_guardrail_indicator("filtered")

            st.session_state.messages.append({"role": "assistant", "content": response_text})


def main() -> None:
    """Main Streamlit application entry point."""
    # Page configuration
    st.set_page_config(
        page_title="Requirements Advisor",
        page_icon="clipboard",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Apply custom branding
    apply_jama_branding()

    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = None
    if "selected_llm" not in st.session_state:
        st.session_state.selected_llm = "claude"

    # Render components
    render_sidebar()
    render_chat()


if __name__ == "__main__":
    main()
