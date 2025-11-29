"""
Streamlit frontend for Requirements Advisor MCP Client.

Provides a chat interface with multi-LLM support and Jama-inspired branding.
"""

import requests
import streamlit as st
import streamlit.components.v1 as components

from requirements_advisor_client.frontend.config import frontend_settings
from requirements_advisor_client.frontend.styles import (
    apply_jama_branding,
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
        # Check backend health once at the start
        health = check_backend_health()

        st.markdown("### Requirements Advisor")
        st.markdown(
            '<p class="subtitle">Agentic RAG + MCP Server Technology Demo</p>',
            unsafe_allow_html=True,
        )

        with st.expander("About This Demo", expanded=False):
            st.markdown("""
**Purpose**: This is a 'Sandbox' jumping-off point proof-of-concept that
demonstrates how Agentic AI can transform requirements management workflows,
serving as a foundation for strategic product discussions.

**What It Demonstrates**:
- Real-time knowledge retrieval from authoritative sources
- Multi-LLM flexibility (Claude, GPT-4o, Gemini)
- Extensible architecture ready for enterprise integration

**Strategic Intent**: Use this baseline to explore practical enhancements that:
- Engage customers and prospects through interactive dialogue
- Differentiate Jama's product offerings
- Drive automated lead qualification and generation
- Create upselling opportunities
            """)

        with st.expander("Strategic Opportunities", expanded=False):
            st.markdown("""
**Potential Product Enhancements**

This architecture enables several high-value capabilities worth exploring:

---

**1. Intelligent Sales Prospecting Tool**

A configurable assistant that:
- Qualifies and profiles users based on conversation context
- Generates summary documents of user interactions
- Provides links to referenced Jama sources and sales/marketing collateral
- Routes qualified leads with profile insights to appropriate sales representatives

---

**2. "Rate My Requirement" Tool**

An analysis tool allowing users to:
- Submit individual requirement records
- Receive structured analysis against INCOSE and EARS standards
- Get actionable enhancement recommendations
- Improve requirement quality systematically

---

**3. "Rate My User Story" Tool**

A companion tool for agile workflows:
- Submit individual User Stories for analysis
- Receive structured evaluation using INCOSE and EARS frameworks
- Get specific suggestions for story improvement
- Bridge the gap between agile practices and requirements rigor
            """)

        # Available tools - directly after Strategic Opportunities
        if health.get("mcp_connected"):
            with st.expander("Available Tools", expanded=False):
                tools = get_available_tools()
                if tools:
                    # Tool count header
                    tool_count = len(tools)
                    st.markdown(
                        f"**{tool_count} tool{'s' if tool_count != 1 else ''} "
                        "available from MCP Server:**"
                    )
                    st.markdown("")  # Spacing

                    for tool in tools:
                        # Tool name in monospace style
                        tool_name = tool.get("name", "unknown")
                        st.markdown(
                            f'<div class="tool-card">'
                            f'<code class="tool-name">{tool_name}</code>'
                            f"</div>",
                            unsafe_allow_html=True,
                        )

                        # Full description (or truncate at 250 chars if very long)
                        description = tool.get("description", "No description available.")
                        if len(description) > 250:
                            description = description[:247] + "..."
                        st.markdown(
                            f'<p class="tool-description">{description}</p>',
                            unsafe_allow_html=True,
                        )
                else:
                    st.markdown("*No tools available*")

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

        # Clear chat button
        if st.button("Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.session_id = None
            st.session_state.has_submitted_prompt = False  # Re-expand quick-start prompts
            st.rerun()

        # Contact section
        st.markdown("---")
        st.markdown(
            """
            <div class="contact-section">
                <p><strong>Questions or Issues?</strong></p>
                <p>Contact: <a href="mailto:afantaci@norfolkaibi.com">afantaci@norfolkaibi.com</a></p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Footer
        st.markdown("---")
        st.markdown(
            "<small>Agentic AI Demo • MCP Server Architecture • Multi-LLM Support</small>",
            unsafe_allow_html=True,
        )


def render_quick_start_prompts() -> None:
    """Render quick-start prompt buttons in an expander.

    The expander is initially expanded but collapses after the user
    submits their first prompt.
    """
    # Initialize tracking for first prompt submission
    if "has_submitted_prompt" not in st.session_state:
        st.session_state.has_submitted_prompt = False

    # Expander is expanded only if user hasn't submitted a prompt yet
    is_expanded = not st.session_state.has_submitted_prompt

    with st.expander("Quick-Start Prompts", expanded=is_expanded):
        st.markdown("*Click to explore:*")

        prompts = [
            "Are there industry-specific considerations when evaluating requirements management solutions?",
            "How should organizations approach requirements traceability for regulatory compliance?",
            "How can requirements management practices support both traditional and agile development methodologies?",
        ]

        for i, prompt in enumerate(prompts):
            if st.button(
                prompt, key=f"quick_prompt_{i}", use_container_width=True, type="secondary"
            ):
                st.session_state.pending_prompt = prompt
                st.session_state.has_submitted_prompt = True
                st.rerun()


def render_chat() -> None:
    """Render the main chat interface."""
    st.title("Requirements Advisor")
    st.markdown(
        '<p class="subtitle">Agentic RAG + MCP Server Technology Demo</p>',
        unsafe_allow_html=True,
    )

    # Description section with auto-hide animation
    st.markdown(
        """
<div id="auto-hide-description" class="fade-out-description">

<p><span class="description-heading">Purpose</span>: This is a 'Sandbox' jumping-off point proof-of-concept that
demonstrates how Agentic AI can transform requirements management workflows,
serving as a foundation for strategic product discussions.</p>

<p><span class="description-heading">What It Demonstrates</span>:</p>
<ul>
<li>Real-time knowledge retrieval from authoritative sources</li>
<li>Multi-LLM flexibility (Claude, GPT-4o, Gemini)</li>
<li>Extensible architecture ready for enterprise integration</li>
</ul>

<p><span class="description-heading">Strategic Intent</span>: Use this baseline to explore practical enhancements that:</p>
<ul>
<li>Engage customers and prospects through interactive dialogue</li>
<li>Differentiate Jama's product offerings</li>
<li>Drive automated lead qualification and generation</li>
<li>Create upselling opportunities</li>
</ul>

</div>
        """,
        unsafe_allow_html=True,
    )

    # JavaScript for auto-hide and blink animation (runs in iframe, accesses parent)
    components.html(
        """
        <script>
            (function() {
                // Access the parent Streamlit document
                var parentDoc = window.parent.document;

                // Set up auto-hide after 5 seconds
                setTimeout(function() {
                    var desc = parentDoc.getElementById('auto-hide-description');
                    if (desc) {
                        desc.style.transition = 'opacity 1s ease-out, max-height 1s ease-out';
                        desc.style.opacity = '0';
                        desc.style.maxHeight = '0';
                        desc.style.overflow = 'hidden';
                        desc.style.marginBottom = '0';
                    }

                    // Trigger blinking on the About This Demo expander
                    var expanders = parentDoc.querySelectorAll(
                        '[data-testid="stSidebar"] [data-testid="stExpander"] summary'
                    );
                    if (expanders.length > 0) {
                        var aboutExpander = expanders[0];
                        aboutExpander.style.animation = 'blink 0.5s ease-in-out infinite';

                        // Stop blinking after 5 seconds
                        setTimeout(function() {
                            aboutExpander.style.animation = '';
                        }, 5000);
                    }
                }, 5000);
            })();
        </script>
        """,
        height=0,
    )

    # Initialize pending_prompt if not exists
    if "pending_prompt" not in st.session_state:
        st.session_state.pending_prompt = None

    # Render quick-start prompts
    render_quick_start_prompts()

    # Process pending prompt if exists
    if st.session_state.pending_prompt:
        prompt = st.session_state.pending_prompt
        st.session_state.pending_prompt = None  # Clear it

        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Get assistant response
        with st.spinner("Thinking..."):
            result = send_chat_message(
                message=prompt,
                session_id=st.session_state.session_id,
                provider=st.session_state.selected_llm,
                history=st.session_state.messages[-10:],
            )

            if "error" in result:
                response_text = f"*Error: {result['error']}*"
            else:
                response_text = result.get("response", "No response received.")
                st.session_state.session_id = result.get("session_id")

            st.session_state.messages.append({"role": "assistant", "content": response_text})

        # Rerun to display messages via history loop (prevents duplication)
        st.rerun()

    # Display conversation history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input(
        "Explore requirements management concepts or discuss strategic enhancements..."
    ):
        # Mark that user has submitted a prompt (collapses quick-start expander)
        st.session_state.has_submitted_prompt = True

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
            else:
                response_text = result.get("response", "No response received.")
                st.session_state.session_id = result.get("session_id")

            st.markdown(response_text)
            st.session_state.messages.append({"role": "assistant", "content": response_text})


def main() -> None:
    """Main Streamlit application entry point."""
    # Page configuration
    st.set_page_config(
        page_title="Requirements Advisor — Agentic AI Proof of Concept",
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
        st.session_state.selected_llm = "gemini"

    # Render components
    render_sidebar()
    render_chat()


if __name__ == "__main__":
    main()
