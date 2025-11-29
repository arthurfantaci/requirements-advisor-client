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

        /* Headers - Main title in Jama orange */
        h1 {{ color: {JAMA_ORANGE}; font-weight: 700; }}
        h2, h3 {{ color: {JAMA_TEXT}; font-weight: 600; }}

        /* Subtitle styling - Jama orange */
        .subtitle {{
            color: {JAMA_ORANGE} !important;
            font-style: italic;
            font-size: 1rem;
            margin-top: -0.5rem;
            margin-bottom: 1rem;
        }}

        /* Description section headings - Jama orange */
        .description-heading {{
            color: {JAMA_ORANGE} !important;
            font-weight: 700;
        }}

        /* Contact section styling */
        .contact-section {{
            font-size: 0.85rem;
        }}

        .contact-section strong {{
            color: {JAMA_ORANGE} !important;
            font-size: 1rem;
        }}

        .contact-section a {{
            color: {JAMA_TEXT_LIGHT} !important;
            text-decoration: underline;
        }}

        .contact-section a:hover {{
            color: {JAMA_ORANGE} !important;
        }}


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

        /* Secondary buttons - quick-start prompts */
        .stButton > button[kind="secondary"] {{
            background-color: {JAMA_BACKGROUND_SECONDARY};
            color: {JAMA_TEXT};
            border: 1px solid {JAMA_BORDER};
            text-align: center;
            font-size: 0.9rem;
            font-weight: 400;
        }}

        .stButton > button[kind="secondary"]:hover {{
            background-color: {JAMA_BORDER};
            border-color: {JAMA_ORANGE};
        }}

        /* Sidebar expander styling - collapsed state */
        [data-testid="stSidebar"] [data-testid="stExpander"] summary {{
            color: {JAMA_TEXT_LIGHT} !important;
            font-weight: 500;
        }}

        [data-testid="stSidebar"] [data-testid="stExpander"] summary span {{
            color: {JAMA_TEXT_LIGHT} !important;
        }}

        [data-testid="stSidebar"] [data-testid="stExpander"] summary svg {{
            fill: {JAMA_TEXT_LIGHT} !important;
        }}

        /* Sidebar expander styling - expanded state (Jama orange) */
        [data-testid="stSidebar"] [data-testid="stExpander"][open] summary,
        [data-testid="stSidebar"] details[open] summary {{
            color: {JAMA_ORANGE} !important;
        }}

        [data-testid="stSidebar"] [data-testid="stExpander"][open] summary span,
        [data-testid="stSidebar"] details[open] summary span {{
            color: {JAMA_ORANGE} !important;
        }}

        [data-testid="stSidebar"] [data-testid="stExpander"][open] summary svg,
        [data-testid="stSidebar"] details[open] summary svg {{
            fill: {JAMA_ORANGE} !important;
        }}

        /* Main content expander styling - expanded state (Jama orange) */
        [data-testid="stExpander"][open] summary,
        [data-testid="stMainBlockContainer"] details[open] summary {{
            color: {JAMA_ORANGE} !important;
        }}

        [data-testid="stExpander"][open] summary span,
        [data-testid="stMainBlockContainer"] details[open] summary span {{
            color: {JAMA_ORANGE} !important;
        }}

        [data-testid="stExpander"][open] summary svg,
        [data-testid="stMainBlockContainer"] details[open] summary svg {{
            fill: {JAMA_ORANGE} !important;
        }}

        /* Sidebar expander content styling */
        [data-testid="stSidebar"] [data-testid="stExpander"] div[data-testid="stExpanderDetails"] {{
            color: {JAMA_TEXT_LIGHT};
            font-size: 0.9rem;
        }}

        /* Sidebar expander content - bold text in Jama orange */
        [data-testid="stSidebar"] [data-testid="stExpander"] div[data-testid="stExpanderDetails"] strong {{
            color: {JAMA_ORANGE} !important;
        }}

        /* Sidebar expander content - horizontal rules styled subtly */
        [data-testid="stSidebar"] [data-testid="stExpander"] div[data-testid="stExpanderDetails"] hr {{
            border-color: rgba(232, 104, 38, 0.3);
            margin: 0.75rem 0;
        }}

        /* Auto-hide description styling */
        .fade-out-description {{
            transition: opacity 1s ease-out, max-height 1s ease-out, margin-bottom 1s ease-out;
            opacity: 1;
            max-height: 1000px;
            overflow: hidden;
        }}

        /* Blink animation for expander */
        @keyframes blink {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.3; }}
        }}

        .blink-animation {{
            animation: blink 0.5s ease-in-out infinite;
        }}

        /* Available Tools styling */
        .tool-card {{
            margin-top: 0.75rem;
            margin-bottom: 0.25rem;
        }}

        .tool-name {{
            background-color: rgba(232, 104, 38, 0.15);
            color: {JAMA_ORANGE};
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace;
            font-size: 0.85rem;
            font-weight: 600;
        }}

        .tool-description {{
            color: {JAMA_TEXT_LIGHT};
            font-size: 0.85rem;
            line-height: 1.4;
            margin-top: 0.25rem;
            margin-bottom: 0.75rem;
            padding-left: 0.25rem;
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
