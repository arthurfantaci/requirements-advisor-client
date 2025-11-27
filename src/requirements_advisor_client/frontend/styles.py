"""
Custom CSS styling for Jama-inspired branding.

Provides consistent visual styling across the Streamlit application
using Jama Software's brand colors and typography.
"""

import streamlit as st

# Jama Brand Colors
JAMA_ORANGE = "#E86826"
JAMA_ORANGE_HOVER = "#D45A1F"
JAMA_DARK = "#1A1A2E"
JAMA_TEXT = "#333333"
JAMA_TEXT_LIGHT = "#E5E7EB"
JAMA_BACKGROUND = "#FFFFFF"
JAMA_BACKGROUND_SECONDARY = "#F8F9FA"
JAMA_BORDER = "#E5E7EB"


def apply_jama_branding() -> None:
    """Apply Jama-inspired custom CSS styling to the Streamlit app.

    Applies:
    - Inter font family for modern typography
    - Jama orange (#E86826) for primary buttons and accents
    - Dark sidebar with light text
    - Styled chat messages and input
    - Hidden Streamlit branding for professional appearance

    Example:
        >>> apply_jama_branding()  # Call at start of main()
    """
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        /* Global typography */
        html, body, [class*="css"] {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }}

        /* Primary buttons - Jama orange */
        .stButton > button {{
            background-color: {JAMA_ORANGE};
            color: white;
            border: none;
            border-radius: 6px;
            padding: 10px 24px;
            font-weight: 600;
            transition: background-color 0.2s ease;
        }}

        .stButton > button:hover {{
            background-color: {JAMA_ORANGE_HOVER};
        }}

        /* Chat messages */
        div[data-testid="stChatMessageContent"] {{
            background-color: {JAMA_BACKGROUND_SECONDARY};
            border-radius: 12px;
            padding: 16px;
            border: 1px solid {JAMA_BORDER};
        }}

        /* Sidebar styling */
        [data-testid="stSidebar"] {{
            background-color: {JAMA_DARK};
        }}

        [data-testid="stSidebar"] .stMarkdown {{
            color: {JAMA_TEXT_LIGHT};
        }}

        [data-testid="stSidebar"] label {{
            color: {JAMA_TEXT_LIGHT} !important;
        }}

        [data-testid="stSidebar"] .stSelectbox label {{
            color: {JAMA_TEXT_LIGHT} !important;
        }}

        /* Chat input */
        .stChatInput > div {{
            border: 2px solid {JAMA_BORDER};
            border-radius: 24px;
        }}

        .stChatInput > div:focus-within {{
            border-color: {JAMA_ORANGE};
        }}

        /* Headers */
        h1 {{ color: {JAMA_DARK}; font-weight: 700; }}
        h2, h3 {{ color: {JAMA_TEXT}; font-weight: 600; }}

        /* Hide Streamlit branding */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        header {{visibility: hidden;}}

        /* Status indicators */
        .status-connected {{
            color: #10B981;
            font-size: 0.875rem;
        }}
        .status-disconnected {{
            color: #EF4444;
            font-size: 0.875rem;
        }}
        </style>
    """,
        unsafe_allow_html=True,
    )


def render_status_indicator(connected: bool, label: str) -> None:
    """Render a status indicator with appropriate styling.

    Args:
        connected: Whether the service is connected/healthy.
        label: Label text to display (e.g., "Backend", "MCP Server").
    """
    status_class = "status-connected" if connected else "status-disconnected"
    status_text = "Connected" if connected else "Disconnected"
    st.markdown(
        f'<span class="{status_class}">{label}: {status_text}</span>',
        unsafe_allow_html=True,
    )
