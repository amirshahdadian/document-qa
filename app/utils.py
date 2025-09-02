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

def handle_error(error: Exception, message: str) -> None:
    """Handle errors with logging and user feedback."""
    logger.error(f"{message}: {str(error)}")
    st.error(f"❌ {message}: {str(error)}")

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
    # Remove old processed auth codes (keep only last 10)
    if 'processed_auth_codes' in st.session_state:
        if len(st.session_state.processed_auth_codes) > 10:
            codes_list = list(st.session_state.processed_auth_codes)
            st.session_state.processed_auth_codes = set(codes_list[-10:])
    
    # Limit chat messages to prevent memory issues (keep last 50)
    if 'messages' in st.session_state:
        if len(st.session_state.messages) > 50:
            st.session_state.messages = st.session_state.messages[-50:]

def debug_chroma_collections():
    """Debug function to list ChromaDB collections."""
    if not IS_PRODUCTION:
        try:
            from app.qa_pipeline import QAPipeline
            qa_pipeline = QAPipeline()
            collections = qa_pipeline.list_collections()
            logger.info(f"Available ChromaDB collections: {collections}")
            return collections
        except Exception as e:
            logger.error(f"Error debugging collections: {e}")
            return []
    return []

def cleanup_old_vector_stores(auth_service, user_id: str, days_old: int = 30):
    """Clean up old vector stores that haven't been accessed recently."""
    try:
        from datetime import datetime, timedelta
        from app.qa_pipeline import QAPipeline
        
        # Get user's chat sessions
        sessions = auth_service.get_chat_history(user_id, limit=100)
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        qa_pipeline = QAPipeline()
        cleaned_count = 0
        
        for session in sessions:
            session_timestamp = session.get('session_timestamp')
            if session_timestamp and session_timestamp < cutoff_date:
                session_id = session.get('id')
                if qa_pipeline.delete_vector_store(user_id, session_id):
                    cleaned_count += 1
        
        logger.info(f"Cleaned up {cleaned_count} old vector stores for user {user_id}")
        return cleaned_count
    except Exception as e:
        logger.error(f"Error cleaning up vector stores: {e}")
        return 0