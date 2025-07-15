import streamlit as st
from app.config import validate_config, AVAILABLE_MODELS, DEFAULT_MODEL, GOOGLE_API_KEY
from app.auth import AuthService
from app.pdf_processing import PDFProcessor
from app.qa_pipeline import QAPipeline
from app.utils import (
    initialize_session_state, format_file_size, handle_error, 
    show_success, show_info, show_warning, format_timestamp, truncate_text
)

def render_authentication_sidebar(auth_service: AuthService):
    """Render the authentication sidebar."""
    with st.sidebar:
        st.header("🔐 Authentication")
        
        if 'user' not in st.session_state:
            tab1, tab2 = st.tabs(["Login", "Register"])
            
            with tab1:
                with st.form("login_form"):
                    email = st.text_input("Email")
                    password = st.text_input("Password", type="password")
                    if st.form_submit_button("Login"):
                        user_data = auth_service.login(email, password)
                        if user_data:
                            st.session_state.user = user_data
                            show_success("Logged in successfully!")
                            st.rerun()
                        else:
                            st.error("Invalid credentials")
            
            with tab2:
                with st.form("register_form"):
                    email = st.text_input("Email")
                    password = st.text_input("Password", type="password")
                    display_name = st.text_input("Display Name")
                    if st.form_submit_button("Register"):
                        user_data = auth_service.register(email, password, display_name)
                        if user_data:
                            st.session_state.user = user_data
                            show_success("Registered successfully!")
                            st.rerun()
                        else:
                            st.error("Registration failed")
        else:
            user_email = st.session_state.user.get('email', 'User')
            st.success(f"Welcome {user_email}")
            if st.button("Logout"):
                auth_service.logout()
                st.rerun()

def render_user_data_sidebar(auth_service: AuthService):
    """Render user documents and chat history in sidebar."""
    if 'user' not in st.session_state:
        return
    
    user_id = st.session_state.user.get('localId')
    if not user_id:
        return
    
    with st.sidebar:
        # User's document history
        st.markdown("---")
        st.subheader("📁 Your Documents")
        documents = auth_service.get_user_documents(user_id)
        if documents:
            for doc in documents[:5]:
                st.text(f"📄 {truncate_text(doc['filename'], 30)} ({format_file_size(doc['file_size'])})")
        else:
            show_info("No documents uploaded yet")
        
        # Previous chat sessions
        st.markdown("---")
        st.subheader("💬 Previous Sessions")
        chat_sessions = auth_service.get_chat_history(user_id, limit=10)
        if chat_sessions:
            session_options = {}
            for session in chat_sessions:
                timestamp = session.get('session_timestamp')
                message_count = session.get('message_count', 0)
                time_str = format_timestamp(timestamp)
                display_name = f"{time_str} ({message_count} msgs)"
                session_options[display_name] = session
            
            session_options["📝 New Session"] = None
            
            selected_session_name = st.selectbox(
                "Select Session:",
                options=list(session_options.keys()),
                key="session_selector"
            )
            
            selected_session = session_options[selected_session_name]
            
            if selected_session and st.button("📖 Load Session"):
                load_chat_session(selected_session)
            
            if selected_session_name == "📝 New Session" and st.button("🆕 New Session"):
                start_new_session()

def load_chat_session(session):
    """Load a previous chat session."""
    try:
        saved_history = session.get('chat_history', [])
        if saved_history and isinstance(saved_history[0], dict):
            st.session_state.chat_history = [
                (item['question'], item['answer']) 
                for item in saved_history
            ]
        else:
            st.session_state.chat_history = saved_history
        
        st.session_state.current_session_id = session.get('id')
        show_success("Session loaded!")
        st.rerun()
    except Exception as e:
        handle_error(e, "Failed to load session")

def start_new_session():
    """Start a new chat session."""
    st.session_state.chat_history = []
    if 'current_session_id' in st.session_state:
        del st.session_state.current_session_id
    show_success("New session started!")
    st.rerun()

def render_configuration_sidebar():
    """Render configuration options in sidebar."""
    with st.sidebar:
        st.markdown("---")
        st.header("⚙️ Configuration")
        
        model = st.selectbox("Select Model:", AVAILABLE_MODELS, index=0)
        temperature = st.slider("Temperature:", 0.0, 1.0, 0.1, 0.1)
        k_docs = st.slider("Retrieved documents:", 1, 10, 5)
        
        st.markdown("---")
        st.markdown("### About")
        st.markdown("This app uses Google's Gemini AI for document Q&A with RAG.")
        
        return model, temperature, k_docs

def render_chat_interface(qa_chain, auth_service):
    """Render the chat interface."""
    st.markdown("---")
    st.header("💬 Ask Questions")
    
    # Display chat history
    if st.session_state.chat_history:
        st.subheader("📜 Chat History")
        for i, (q, a) in enumerate(st.session_state.chat_history):
            with st.container():
                st.markdown(f"**Q{i+1}:** {q}")
                st.markdown(f"**A{i+1}:** {a}")
                st.markdown("---")
    
    # Question input
    question = st.text_input(
        "Ask a question about the document:",
        placeholder="e.g., What is the main topic of this document?"
    )
    
    # Action buttons
    col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
    
    with col1:
        ask_button = st.button("🚀 Ask", type="primary")
    
    with col2:
        if st.button("🗑️ Clear History"):
            st.session_state.chat_history = []
            if 'current_session_id' in st.session_state:
                del st.session_state.current_session_id
            st.rerun()
    
    with col3:
        if st.button("💾 Save Session"):
            save_current_session(auth_service)
    
    with col4:
        if st.button("🔄 Refresh"):
            st.rerun()
    
    # Process question
    if question and ask_button:
        try:
            qa_pipeline = QAPipeline()
            with st.spinner("🔍 Searching for answer..."):
                result = qa_pipeline.ask_question(qa_chain, question)
                
                # Add to chat history
                st.session_state.chat_history.append((question, result["answer"]))
                
                # Display answer
                st.markdown("### 💡 Answer:")
                st.markdown(result["answer"])
                
                # Show sources
                if result.get("source_documents"):
                    with st.expander("📖 Source Documents"):
                        for i, doc in enumerate(result["source_documents"]):
                            st.markdown(f"**Source {i+1}:**")
                            content = doc.page_content[:500] + "..." if len(doc.page_content) > 500 else doc.page_content
                            st.text_area(f"Content {i+1}:", content, height=100, key=f"source_{i}_{len(st.session_state.chat_history)}")
                            if doc.metadata:
                                st.json(doc.metadata)
                            st.markdown("---")
                
                st.rerun()
        except Exception as e:
            handle_error(e, "Error generating answer")

def save_current_session(auth_service):
    """Save the current chat session."""
    user_id = st.session_state.user.get('localId')
    if user_id and st.session_state.chat_history:
        session_id = auth_service.save_chat_history(user_id, st.session_state.chat_history)
        if session_id:
            st.session_state.current_session_id = session_id
            show_success("Session saved!")
        else:
            st.error("Failed to save session")

def main():
    """Main application function."""
    st.set_page_config(
        page_title="PDF Q&A with RAG",
        page_icon="📚",
        layout="wide"
    )
    
    # Validate configuration
    if not validate_config():
        st.error("❌ Configuration validation failed. Please check your environment variables.")
        return
    
    # Initialize session state
    initialize_session_state()
    
    # Initialize services
    auth_service = AuthService()
    pdf_processor = PDFProcessor()
    qa_pipeline = QAPipeline()
    
    # Render authentication
    render_authentication_sidebar(auth_service)
    
    # Main app content
    if 'user' not in st.session_state:
        st.title("📚 PDF Document Q&A with RAG")
        show_warning("Please login to access the PDF Q&A system")
        st.markdown("This app uses Google's Gemini AI to answer questions about your PDF documents using RAG (Retrieval Augmented Generation).")
        return
    
    # Render user data sidebar
    render_user_data_sidebar(auth_service)
    
    # Render main interface
    st.title("📚 PDF Document Q&A with RAG (Gemini)")
    st.markdown("Upload a PDF document and ask questions about its content!")
    
    # Show current session info
    if 'current_session_id' in st.session_state:
        show_info(f"Current Session: {st.session_state.current_session_id}")
    else:
        show_info("Current Session: New (not saved)")
    
    # Configuration sidebar
    selected_model, temperature, k_docs = render_configuration_sidebar()
    
    # File upload
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Upload a PDF file", 
            type="pdf",
            help="Maximum file size: 50MB"
        )
    
    with col2:
        if uploaded_file:
            show_info(f"File: {uploaded_file.name}")
            show_info(f"Size: {format_file_size(uploaded_file.size)}")
    
    # Process PDF
    if uploaded_file is not None:
        if st.button("🔄 Process PDF", type="primary"):
            try:
                with st.spinner("Processing PDF..."):
                    # Process PDF
                    chunks = pdf_processor.load_and_process_pdf(uploaded_file)
                    
                    # Create vector store
                    vector_store = qa_pipeline.create_vector_store(chunks)
                    st.session_state.vector_store = vector_store
                    
                    # Setup QA chain
                    qa_chain = qa_pipeline.setup_qa_chain(
                        vector_store, 
                        model=selected_model,
                        temperature=temperature,
                        k_docs=k_docs
                    )
                    st.session_state.qa_chain = qa_chain
                    
                    # Save document metadata
                    user_id = st.session_state.user.get('localId')
                    if user_id:
                        auth_service.save_document_metadata(
                            user_id, 
                            uploaded_file.name, 
                            uploaded_file.size, 
                            len(chunks)
                        )
                    
                    show_success(f"PDF processed! {len(chunks)} chunks created.")
                    
            except Exception as e:
                handle_error(e, "Error processing PDF")
    
    # Chat interface
    if st.session_state.qa_chain is not None:
        render_chat_interface(st.session_state.qa_chain, auth_service)
    else:
        show_info("Please upload and process a PDF file first.")

if __name__ == "__main__":
    main()