import logging
import streamlit as st
from typing import Any, Optional

logger = logging.getLogger(__name__)

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def safe_get_session_state(key: str, default: Any = None) -> Any:
    """Safely get value from session state."""
    return st.session_state.get(key, default)

def set_session_state(key: str, value: Any) -> None:
    """Set value in session state."""
    st.session_state[key] = value

def clear_session_state(key: str) -> None:
    """Clear specific key from session state."""
    if key in st.session_state:
        del st.session_state[key]

def initialize_session_state() -> None:
    """Initialize default session state values."""
    defaults = {
        "vector_store": None,
        "qa_chain": None,
        "chat_history": [],
        "current_session_id": None,
        "processed_document": None
    }
    
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

def handle_error(e: Exception, message: str = "An error occurred.") -> None:
    """Handle and display errors in a standardized way."""
    logger.error(f"{message}: {e}", exc_info=True)
    st.error(message)

def show_success(message: str) -> None:
    """Show success message with logging."""
    logger.info(message)
    st.success(f"✅ {message}")

def show_info(message: str) -> None:
    """Show info message."""
    st.info(f"ℹ️ {message}")

def show_warning(message: str) -> None:
    """Show warning message."""
    st.warning(f"⚠️ {message}")

def format_timestamp(timestamp) -> str:
    """Format timestamp for display."""
    try:
        if hasattr(timestamp, 'strftime'):
            return timestamp.strftime("%m/%d/%Y %H:%M")
        else:
            return "Unknown time"
    except Exception:
        return "Unknown time"

def truncate_text(text: str, max_length: int = 50) -> str:
    """Truncate text to maximum length."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."

def cleanup_session_state():
    """Clean up old session state data to prevent memory issues."""
    # Remove old processed auth codes, keeping only the last 10
    if 'processed_auth_codes' in st.session_state:
        if len(st.session_state.processed_auth_codes) > 10:
            codes_list = list(st.session_state.processed_auth_codes)
            st.session_state.processed_auth_codes = set(codes_list[-10:])
    
    # Limit chat messages to last 50 to prevent memory issues
    if 'messages' in st.session_state:
        if len(st.session_state.messages) > 50:
            st.session_state.messages = st.session_state.messages[-50:]