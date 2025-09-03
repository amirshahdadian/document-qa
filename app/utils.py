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