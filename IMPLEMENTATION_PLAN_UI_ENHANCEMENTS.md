# Implementation Plan: Requirements Advisor Client UI Enhancements

## Overview

This document provides Claude Code with a comprehensive implementation plan for enhancing the Requirements Advisor Client web application UI. The goal is to better position this application as a strategic proof-of-concept for Jama Software senior executives, demonstrating the potential of Agentic RAG and MCP Server architectures.

## Target Audience

Jama Software senior executives including:
- CEO
- Chief Strategy Officer
- Leader of Product & Engineering
- Vice President of Solutions & Support

## Current State

The existing UI in `src/requirements_advisor_client/frontend/app.py` contains generic descriptive text that does not adequately communicate:
- The strategic purpose of the application as a proof-of-concept
- The Agentic AI and MCP architecture being demonstrated
- Potential product enhancement opportunities

---

## Implementation Requirements

### 1. Update Page Title and Metadata

**File**: `src/requirements_advisor_client/frontend/app.py`

**Location**: `main()` function, `st.set_page_config()` call

**Changes**:
```python
st.set_page_config(
    page_title="Requirements Advisor — Agentic AI Proof of Concept",
    page_icon="clipboard",
    layout="wide",
    initial_sidebar_state="expanded",
)
```

---

### 2. Update Sidebar Header and Structure

**File**: `src/requirements_advisor_client/frontend/app.py`

**Location**: `render_sidebar()` function

**Replace the current sidebar header**:
```python
# Current:
st.markdown("### Requirements Advisor")
st.markdown("*Expert guidance on requirements management*")

# Replace with:
st.markdown("### Requirements Advisor")
st.markdown("*Agentic RAG + MCP Server Technology Demo*")
```

---

### 3. Add "About This Demo" Expander

**File**: `src/requirements_advisor_client/frontend/app.py`

**Location**: `render_sidebar()` function, immediately after the header/subtitle

**Add new expander section**:
```python
with st.expander("About This Demo", expanded=False):
    st.markdown("""
**Purpose**: This proof-of-concept demonstrates how Agentic AI can transform 
requirements management workflows, serving as a foundation for strategic 
product discussions.

**What It Demonstrates**:
- Real-time knowledge retrieval from authoritative sources
- Intelligent synthesis across INCOSE guidelines, EARS notation, and Jama best practices
- Multi-LLM flexibility (Claude, GPT-4o, Gemini)
- Extensible architecture ready for enterprise integration

**Strategic Intent**: Use this baseline to explore practical enhancements 
that could differentiate Jama's product offerings and deliver new customer value.
    """)
```

---

### 4. Add "Strategic Opportunities" Expander

**File**: `src/requirements_advisor_client/frontend/app.py`

**Location**: `render_sidebar()` function, immediately after the "About This Demo" expander

**Add new expander section**:
```python
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
```

---

### 5. Update Main Content Description

**File**: `src/requirements_advisor_client/frontend/app.py`

**Location**: `render_chat()` function

**Replace the current description**:
```python
# Current:
st.title("Requirements Advisor")
st.markdown(
    "Ask questions about requirements management best practices, "
    "INCOSE guidelines, EARS notation, and more."
)

# Replace with:
st.title("Requirements Advisor")
st.markdown("""
This proof-of-concept demonstrates how Agentic RAG (Retrieval-Augmented Generation) 
and the Model Context Protocol (MCP) can transform requirements management workflows.

Built as a strategic exploration platform, this application showcases:
- **Real-time retrieval** from authoritative sources (INCOSE, EARS, Jama best practices)
- **Multi-LLM orchestration** with tool-calling capabilities
- **A modular, extensible architecture** ready for enterprise integration

Use this baseline to explore practical enhancements—from automated requirements 
validation to intelligent traceability analysis—that could differentiate Jama's 
product offerings.
""")
```

---

### 6. Add Quick-Start Prompts

**File**: `src/requirements_advisor_client/frontend/app.py`

**Location**: `render_chat()` function, after the main description and BEFORE the chat history display

**Implementation approach**: Create clickable buttons that populate the chat input when clicked

**Add new function and integrate into render_chat()**:

```python
def render_quick_start_prompts() -> str | None:
    """Render quick-start prompt buttons and return selected prompt if clicked.
    
    Returns:
        The selected prompt text if a button was clicked, None otherwise.
    """
    st.markdown("**Quick-Start Prompts** — Click to explore:")
    
    prompts = [
        "Are there industry-specific considerations when evaluating requirements management solutions?",
        "What are the key differences between EARS notation patterns for complex system requirements?",
        "How should organizations approach requirements traceability for regulatory compliance?",
        "What does INCOSE recommend for validating requirements quality at scale?",
        "How can requirements management practices support both traditional and agile development methodologies?",
    ]
    
    # Create columns for button layout (adjust as needed for visual preference)
    # Using 1 column per prompt for readability given prompt length
    selected_prompt = None
    
    for prompt in prompts:
        # Truncate display text if needed, but store full prompt
        display_text = prompt if len(prompt) <= 80 else prompt[:77] + "..."
        if st.button(display_text, key=f"prompt_{hash(prompt)}", use_container_width=True):
            selected_prompt = prompt
    
    st.markdown("---")
    
    return selected_prompt
```

**Integrate into render_chat()**:

```python
def render_chat() -> None:
    """Render the main chat interface."""
    st.title("Requirements Advisor")
    st.markdown("""
    [Updated description as specified above]
    """)
    
    # Quick-start prompts section
    selected_prompt = render_quick_start_prompts()
    
    # Handle quick-start prompt selection
    if selected_prompt:
        # Add to messages and trigger response
        st.session_state.messages.append({"role": "user", "content": selected_prompt})
        st.rerun()
    
    # Display conversation history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # [Rest of existing chat input handling...]
```

**Important**: The quick-start prompt handling needs careful integration with the existing chat flow. When a prompt button is clicked, it should:
1. Add the prompt as a user message to session state
2. Trigger a rerun that processes the message through the normal chat flow

**Alternative implementation** (if the above causes issues with message processing):

```python
def render_quick_start_prompts() -> None:
    """Render quick-start prompt buttons that set a session state flag."""
    st.markdown("**Quick-Start Prompts** — Click to explore:")
    
    prompts = [
        "Are there industry-specific considerations when evaluating requirements management solutions?",
        "What are the key differences between EARS notation patterns for complex system requirements?",
        "How should organizations approach requirements traceability for regulatory compliance?",
        "What does INCOSE recommend for validating requirements quality at scale?",
        "How can requirements management practices support both traditional and agile development methodologies?",
    ]
    
    for i, prompt in enumerate(prompts):
        if st.button(prompt, key=f"quick_prompt_{i}", use_container_width=True):
            st.session_state.pending_prompt = prompt
            st.rerun()
    
    st.markdown("---")


def render_chat() -> None:
    """Render the main chat interface."""
    st.title("Requirements Advisor")
    st.markdown("""...""")  # Updated description
    
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
        
        # Get assistant response (same logic as existing chat input handler)
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
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
                
                st.markdown(response_text)
                st.session_state.messages.append(
                    {"role": "assistant", "content": response_text}
                )
    
    # Display conversation history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input (existing code)
    if prompt := st.chat_input("Explore requirements management concepts or discuss strategic enhancements..."):
        # [existing chat input handling code]
```

---

### 7. Update Chat Input Placeholder

**File**: `src/requirements_advisor_client/frontend/app.py`

**Location**: `render_chat()` function, `st.chat_input()` call

**Change**:
```python
# Current:
if prompt := st.chat_input("Ask about requirements management..."):

# Replace with:
if prompt := st.chat_input("Explore requirements management concepts or discuss strategic enhancements..."):
```

---

### 8. Update Footer

**File**: `src/requirements_advisor_client/frontend/app.py`

**Location**: `render_sidebar()` function, footer section at bottom

**Change**:
```python
# Current:
st.markdown(
    "<small>Powered by MCP + LiteLLM</small>",
    unsafe_allow_html=True,
)

# Replace with:
st.markdown(
    "<small>Agentic AI Demo • MCP Server Architecture • Multi-LLM Support</small>",
    unsafe_allow_html=True,
)
```

---

### 9. Optional: Add Custom Styling for New Elements

**File**: `src/requirements_advisor_client/frontend/styles.py`

**Location**: `apply_jama_branding()` function

**Add styling for quick-start prompt buttons** (if default styling is insufficient):

```python
# Add to the CSS string in apply_jama_branding():

/* Quick-start prompt buttons - secondary style */
div[data-testid="stButton"] button[kind="secondary"] {
    background-color: {JAMA_BACKGROUND_SECONDARY};
    color: {JAMA_TEXT};
    border: 1px solid {JAMA_BORDER};
    text-align: left;
    font-size: 0.9rem;
}

div[data-testid="stButton"] button[kind="secondary"]:hover {
    background-color: {JAMA_BORDER};
    border-color: {JAMA_ORANGE};
}

/* Expander styling for sidebar */
[data-testid="stSidebar"] .streamlit-expanderHeader {
    color: {JAMA_TEXT_LIGHT};
    font-weight: 500;
}

[data-testid="stSidebar"] .streamlit-expanderContent {
    color: {JAMA_TEXT_LIGHT};
    font-size: 0.9rem;
}
```

---

## Implementation Order

Execute changes in this order to minimize integration issues:

1. **Update page title and metadata** (simple change, no dependencies)
2. **Update sidebar header text** (simple change)
3. **Add "About This Demo" expander** (new section, no dependencies)
4. **Add "Strategic Opportunities" expander** (new section, after About)
5. **Update main content description** (simple change)
6. **Update chat input placeholder** (simple change)
7. **Update footer** (simple change)
8. **Add quick-start prompts** (most complex, do last)
9. **Add custom styling** (if needed after testing)

---

## Testing Checklist

After implementation, verify:

- [ ] Page title shows "Requirements Advisor — Agentic AI Proof of Concept" in browser tab
- [ ] Sidebar header displays updated subtitle
- [ ] "About This Demo" expander opens/closes correctly and displays content
- [ ] "Strategic Opportunities" expander opens/closes correctly and displays all three opportunities
- [ ] Main description renders with bullet points and bold text correctly
- [ ] All five quick-start prompt buttons are visible
- [ ] Clicking a quick-start prompt populates it as a user message
- [ ] Quick-start prompt triggers LLM response correctly
- [ ] Chat input placeholder shows updated text
- [ ] Footer displays updated text
- [ ] All styling maintains Jama orange (#E86826) branding
- [ ] Application remains responsive and functional
- [ ] No console errors in browser developer tools

---

## Files Modified

| File | Type of Change |
|------|----------------|
| `src/requirements_advisor_client/frontend/app.py` | Major updates: new functions, updated text, restructured render functions |
| `src/requirements_advisor_client/frontend/styles.py` | Minor updates: optional CSS additions for new elements |

---

## Rollback Plan

If issues arise, the original `app.py` can be restored from version control. All changes are confined to frontend files and do not affect:
- Backend API functionality
- Database schema
- MCP server connection
- LLM integration

---

## Notes for Implementation

1. **Streamlit Session State**: The quick-start prompts implementation requires careful handling of Streamlit's session state and rerun behavior. Test thoroughly to ensure prompts trigger the full chat flow.

2. **Button Styling**: Streamlit's default button styling may make the quick-start prompts visually prominent. If they appear too similar to primary action buttons, consider using `st.button(..., type="secondary")` if available in your Streamlit version, or apply custom CSS.

3. **Text Length**: The quick-start prompts are intentionally verbose to demonstrate the type of strategic questions executives might explore. If they render poorly on smaller screens, consider responsive design adjustments.

4. **Expander Default State**: Both "About This Demo" and "Strategic Opportunities" are set to `expanded=False` to keep the sidebar clean by default. Executives can expand sections as needed.

5. **Markdown Rendering**: The Strategic Opportunities section uses horizontal rules (`---`) to separate the three opportunities. Verify these render correctly in the sidebar context.
