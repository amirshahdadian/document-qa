import streamlit as st
from datetime import datetime
from app.config import validate_config, AVAILABLE_MODELS, DEFAULT_MODEL
from app.auth import AuthService
from app.pdf_processing import PDFProcessor
from app.qa_pipeline import QAPipeline
from app.utils import (
    initialize_session_state, format_file_size, handle_error, 
    show_success, show_info, show_warning, format_timestamp
)

def initialize_simple_session_state():
    """Initialize minimal session state for simple UI."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "qa_chain" not in st.session_state:
        st.session_state.qa_chain = None
    if "document_processed" not in st.session_state:
        st.session_state.document_processed = False
    if "current_document" not in st.session_state:
        st.session_state.current_document = None
    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = None
    if "current_session_title" not in st.session_state:
        st.session_state.current_session_title = "New Chat"
    if "auth_service" not in st.session_state:
        st.session_state.auth_service = AuthService()

def render_auth_section():
    """Render authentication section in main area when not logged in."""
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1>🇮🇹 Italian Student Document Assistant</h1>
        <p style="font-size: 1.2rem; color: #666;">Upload your Italian student documents and get instant answers</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Create columns for centering
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### 🔐 Welcome! Please sign in to continue")
        
        # Create tabs for login and register
        tab1, tab2 = st.tabs(["🔑 Sign In", "👤 Create Account"])
        
        with tab1:
            with st.form("login_form", clear_on_submit=True):
                st.markdown("#### Sign in to your account")
                email = st.text_input("Email Address", placeholder="your.email@example.com")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                
                if st.form_submit_button("🚀 Sign In", use_container_width=True, type="primary"):
                    if email and password:
                        with st.spinner("Signing in..."):
                            user_data = st.session_state.auth_service.login(email, password)
                            if user_data:
                                st.session_state.user = user_data
                                st.success("✅ Signed in successfully!")
                                st.rerun()
                            else:
                                st.error("❌ Invalid email or password. Please try again.")
                    else:
                        st.error("❌ Please fill in both email and password.")
        
        with tab2:
            with st.form("register_form", clear_on_submit=True):
                st.markdown("#### Create a new account")
                email = st.text_input("Email Address", placeholder="your.email@example.com")
                password = st.text_input("Password", type="password", placeholder="Choose a strong password")
                password_confirm = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")
                display_name = st.text_input("Display Name", placeholder="Your name (optional)")
                
                if st.form_submit_button("🎯 Create Account", use_container_width=True, type="primary"):
                    if email and password and password_confirm:
                        if password != password_confirm:
                            st.error("❌ Passwords do not match.")
                        elif len(password) < 6:
                            st.error("❌ Password must be at least 6 characters long.")
                        else:
                            with st.spinner("Creating account..."):
                                user_data = st.session_state.auth_service.register(email, password, display_name)
                                if user_data:
                                    st.session_state.user = user_data
                                    st.success("✅ Account created successfully!")
                                    st.rerun()
                                else:
                                    st.error("❌ Failed to create account. Email might already be in use.")
                    else:
                        st.error("❌ Please fill in all required fields.")
    
    # About section
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; padding: 2rem;">
        <h3>🎓 Perfect for International Students in Italy</h3>
        <p style="font-size: 1.1rem; color: #666;">
            This app helps you understand complex Italian documents such as:
        </p>
        <div style="display: flex; justify-content: center; gap: 2rem; margin-top: 1rem;">
            <div>📋 <strong>Bandi</strong><br><small>Scholarship calls</small></div>
            <div>📜 <strong>Regolamenti</strong><br><small>University rules</small></div>
            <div>🏠 <strong>Contratti</strong><br><small>Housing contracts</small></div>
            <div>📝 <strong>Modulistica</strong><br><small>Application forms</small></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_chat_sidebar():
    """Render chat history sidebar."""
    with st.sidebar:
        # New Chat button
        if st.button("➕ New Chat", use_container_width=True, type="primary"):
            start_new_chat()
        
        st.markdown("---")
        
        # Chat History
        st.markdown("### 💬 Chat History")
        
        if 'user' in st.session_state:
            user_id = st.session_state.user.get('localId')
            if user_id:
                chat_sessions = st.session_state.auth_service.get_chat_history(user_id, limit=20)
                
                if chat_sessions:
                    # Create a scrollable container
                    chat_container = st.container()
                    with chat_container:
                        for session in chat_sessions:
                            session_id = session.get('id')
                            session_title = session.get('session_title', 'Untitled Chat')
                            timestamp = session.get('session_timestamp')
                            message_count = session.get('message_count', 0)
                            
                            # Format timestamp
                            time_str = format_timestamp(timestamp) if timestamp else "Unknown"
                            
                            # Truncate title if too long
                            display_title = session_title[:30] + "..." if len(session_title) > 30 else session_title
                            
                            # Check if this is the current session
                            is_current = st.session_state.current_session_id == session_id
                            
                            # Create columns for chat button and delete button
                            col1, col2 = st.columns([4, 1])
                            
                            with col1:
                                # Create button with session info
                                button_text = f"📄 {display_title}"
                                if is_current:
                                    button_text = f"🔹 {display_title}"
                                
                                if st.button(
                                    button_text,
                                    key=f"chat_{session_id}",
                                    help=f"{time_str} • {message_count} messages",
                                    use_container_width=True,
                                    disabled=is_current
                                ):
                                    load_chat_session(session)
                            
                            with col2:
                                # Delete button
                                if st.button(
                                    "🗑️",
                                    key=f"delete_{session_id}",
                                    help="Delete this chat session",
                                    use_container_width=True,
                                    type="secondary"
                                ):
                                    delete_chat_session(session_id, session_title)
                            
                            # Show session details
                            st.caption(f"🕒 {time_str}")
                            st.markdown("---")
                else:
                    st.info("No previous chats found")
        
        st.markdown("---")
        
        # Settings dropdown
        with st.expander("⚙️ Settings"):
            # Model selection
            model = st.selectbox(
                "AI Model:",
                AVAILABLE_MODELS,
                index=0,
                help="Choose the AI model for processing"
            )
            
            # Temperature setting
            temperature = st.slider(
                "Response Style:",
                0.0, 1.0, 0.1, 0.1,
                help="0 = Factual, 1 = Creative"
            )
        
        # User info
        if 'user' in st.session_state:
            st.markdown("---")
            user_email = st.session_state.user.get('email', 'User')
            st.caption(f"👤 {user_email}")
            
            if st.button("🚪 Sign Out", use_container_width=True, type="secondary"):
                sign_out_user()

def start_new_chat():
    """Start a new chat session."""
    # Reset session state for new chat
    st.session_state.messages = []
    st.session_state.qa_chain = None
    st.session_state.document_processed = False
    st.session_state.current_document = None
    st.session_state.current_session_id = None
    st.session_state.current_session_title = "New Chat"
    st.rerun()

def load_chat_session(session):
    """Load a previous chat session."""
    try:
        # Load session data
        st.session_state.current_session_id = session.get('id')
        st.session_state.current_session_title = session.get('session_title', 'Untitled Chat')
        
        # Load chat history
        saved_history = session.get('chat_history', [])
        messages = []
        
        # Convert chat history to messages format
        for item in saved_history:
            if isinstance(item, dict):
                # New format
                messages.append({"role": "user", "content": item.get('question', '')})
                messages.append({"role": "assistant", "content": item.get('answer', '')})
            else:
                # Legacy format (tuple)
                question, answer = item
                messages.append({"role": "user", "content": question})
                messages.append({"role": "assistant", "content": answer})
        
        st.session_state.messages = messages
        
        # Set document as processed (assume it was processed in the original session)
        st.session_state.document_processed = True
        st.session_state.current_document = session.get('document_name', 'Previous Document')
        
        # Note: We can't restore the QA chain, so user will need to re-upload document for new questions
        st.session_state.qa_chain = None
        
        show_success(f"Loaded chat session: {st.session_state.current_session_title}")
        st.rerun()
    except Exception as e:
        handle_error(e, "Failed to load chat session")

def sign_out_user():
    """Sign out the current user."""
    st.session_state.auth_service.logout()
    # Clear all session state except auth_service
    for key in list(st.session_state.keys()):
        if key not in ['auth_service']:
            del st.session_state[key]
    st.rerun()

def render_header():
    """Render the main header."""
    st.markdown(f"""
    <div style="margin-bottom: 1rem;">
        <h1 style="margin: 0;">🇮🇹 Italian Student Document Assistant</h1>
        <p style="margin: 0; font-size: 1rem; color: #666;">
            {st.session_state.current_session_title}
        </p>
    </div>
    """, unsafe_allow_html=True)

def render_document_upload():
    """Render the document upload section."""
    if not st.session_state.document_processed:
        st.markdown("### 📁 Upload Your Document")
        st.info("📋 Each chat session requires one document. Upload a new document to start chatting!")
        
        with st.container():
            uploaded_file = st.file_uploader(
                "Choose a PDF file",
                type="pdf",
                help="Upload Italian student documents: bandi, regolamenti, contratti, etc. (Max: 50MB)"
            )
            
            if uploaded_file:
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.info(f"📄 **{uploaded_file.name}** ({format_file_size(uploaded_file.size)})")
                
                with col2:
                    if st.button("🚀 Process Document", type="primary", use_container_width=True):
                        process_document(uploaded_file)
        
        # Show example questions while waiting
        if not uploaded_file:
            render_example_questions()
    else:
        # Show current document info
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.success(f"✅ **{st.session_state.current_document}** - Ready for questions!")
        
        with col2:
            if st.button("📄 New Document", type="secondary", use_container_width=True):
                start_new_chat()

def process_document(uploaded_file):
    """Process the uploaded document and create/update session."""
    try:
        with st.spinner("🔍 Processing your document... This may take a moment."):
            # Initialize processors
            pdf_processor = PDFProcessor()
            qa_pipeline = QAPipeline()
            
            # Process PDF
            chunks = pdf_processor.load_and_process_pdf(uploaded_file)
            
            # Create vector store
            vector_store = qa_pipeline.create_vector_store(chunks)
            
            # Setup QA chain
            qa_chain = qa_pipeline.setup_qa_chain(vector_store)
            
            # Create session title from document name and timestamp
            timestamp = datetime.now().strftime("%m/%d %H:%M")
            session_title = f"{uploaded_file.name} - {timestamp}"
            
            # Update session state
            st.session_state.qa_chain = qa_chain
            st.session_state.document_processed = True
            st.session_state.current_document = uploaded_file.name
            st.session_state.current_session_title = session_title
            
            # Create new session in Firestore
            user_id = st.session_state.user.get('localId')
            if user_id:
                session_id = create_new_session(user_id, session_title, uploaded_file.name)
                st.session_state.current_session_id = session_id
                
                # Save document metadata
                st.session_state.auth_service.save_document_metadata(
                    user_id, uploaded_file.name, uploaded_file.size, len(chunks)
                )
            
            # Add system message
            st.session_state.messages.append({
                "role": "system",
                "content": f"Document **{uploaded_file.name}** has been processed successfully! You can now ask questions about it."
            })
            
            show_success("✅ Document processed successfully!")
            st.rerun()
            
    except Exception as e:
        handle_error(e, "Error processing document")

def create_new_session(user_id: str, session_title: str, document_name: str):
    """Create a new chat session in Firestore."""
    try:
        from firebase_admin import firestore
        db = firestore.client()
        
        doc_ref = db.collection('users').document(user_id).collection('chat_sessions').document()
        doc_ref.set({
            'session_title': session_title,
            'document_name': document_name,
            'session_timestamp': datetime.now(),
            'message_count': 0,
            'chat_history': [],
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        })
        
        return doc_ref.id
    except Exception as e:
        print(f"Error creating session: {e}")
        return None

def auto_save_message(user_id: str, session_id: str, question: str, answer: str):
    """Automatically save each Q&A pair to Firestore."""
    try:
        from firebase_admin import firestore
        db = firestore.client()
        
        # Get current session
        session_ref = db.collection('users').document(user_id).collection('chat_sessions').document(session_id)
        session_doc = session_ref.get()
        
        if session_doc.exists:
            session_data = session_doc.to_dict()
            current_history = session_data.get('chat_history', [])
            
            # Add new message
            new_message = {
                'question': question,
                'answer': answer,
                'timestamp': datetime.now()
            }
            current_history.append(new_message)
            
            # Update session
            session_ref.update({
                'chat_history': current_history,
                'message_count': len(current_history),
                'updated_at': datetime.now()
            })
            
            return True
    except Exception as e:
        print(f"Error auto-saving message: {e}")
        return False

def render_example_questions():
    """Render example questions."""
    st.markdown("### 💡 Example Questions You Can Ask")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **📋 For Bandi (Announcements):**
        - What are the eligibility criteria?
        - What is the application deadline?
        - What documents do I need to submit?
        - How much is the scholarship amount?
        """)
    
    with col2:
        st.markdown("""
        **📜 For Regolamenti (Regulations):**
        - What are the attendance requirements?
        - What are the exam rules?
        - What are the consequences for violations?
        - Summarize the main points
        """)

def render_chat_interface():
    """Render the chat interface."""
    if not st.session_state.document_processed:
        return
    
    st.markdown("### 💬 Chat")
    
    # Create chat container
    chat_container = st.container()
    
    with chat_container:
        # Display chat messages
        for msg_idx, message in enumerate(st.session_state.messages):
            if message["role"] == "user":
                with st.chat_message("user"):
                    st.write(message["content"])
            elif message["role"] == "assistant":
                with st.chat_message("assistant"):
                    st.write(message["content"])
                    # Show sources if available
                    if "sources" in message:
                        with st.expander("📖 View Sources"):
                            for i, source in enumerate(message["sources"][:3]):
                                st.markdown(f"**Source {i+1}:**")
                                content = source.page_content[:200] + "..." if len(source.page_content) > 200 else source.page_content
                                st.text_area(
                                    f"Content {i+1}:", 
                                    content, 
                                    height=80, 
                                    key=f"source_msg_{msg_idx}_src_{i}",
                                    disabled=True
                                )
            elif message["role"] == "system":
                st.info(message["content"])
    
    # Quick action buttons
    st.markdown("### 🚀 Quick Actions")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📄 Summarize Document", use_container_width=True):
            handle_quick_action("Please provide a comprehensive summary of this document, highlighting the main points, important dates, requirements, and key information.")
    
    with col2:
        if st.button("🎯 Key Points", use_container_width=True):
            handle_quick_action("Extract the most important key points from this document in bullet format, focusing on deadlines, requirements, and procedures.")
    
    with col3:
        if st.button("📋 Eligibility Criteria", use_container_width=True):
            handle_quick_action("What are the eligibility criteria mentioned in this document?")
    
    # Chat input
    if prompt := st.chat_input("Ask a question about your document..."):
        handle_user_input(prompt)

def handle_quick_action(prompt):
    """Handle quick action button clicks."""
    st.session_state.messages.append({"role": "user", "content": prompt})
    process_question(prompt)
    st.rerun()

def handle_user_input(prompt):
    """Handle user input from chat."""
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Process the question
    process_question(prompt)
    
    # Rerun to show the response
    st.rerun()

def process_question(question):
    """Process a question and add response to messages."""
    try:
        with st.spinner("🤔 Thinking..."):
            qa_pipeline = QAPipeline()
            result = qa_pipeline.ask_question(st.session_state.qa_chain, question)
            
            # Add assistant response
            assistant_message = {
                "role": "assistant",
                "content": result["answer"]
            }
            
            # Add sources if available
            if result.get("source_documents"):
                assistant_message["sources"] = result["source_documents"]
            
            st.session_state.messages.append(assistant_message)
            
            # Auto-save to Firestore
            if 'user' in st.session_state and st.session_state.current_session_id:
                user_id = st.session_state.user.get('localId')
                auto_save_message(user_id, st.session_state.current_session_id, question, result["answer"])
            
    except Exception as e:
        error_message = f"❌ Sorry, I encountered an error: {str(e)}"
        st.session_state.messages.append({
            "role": "assistant",
            "content": error_message
        })

def delete_chat_session(session_id: str, session_title: str):
    """Delete a chat session."""
    try:
        user_id = st.session_state.user.get('localId')
        if user_id:
            success = st.session_state.auth_service.delete_chat_session(user_id, session_id)
            if success:
                # If we're deleting the current session, start a new chat
                if st.session_state.current_session_id == session_id:
                    start_new_chat()
                else:
                    show_success(f"Deleted chat session: {session_title}")
                    st.rerun()
            else:
                st.error("❌ Failed to delete chat session")
    except Exception as e:
        handle_error(e, "Failed to delete chat session")

def main():
    """Main application function."""
    # Page config
    st.set_page_config(
        page_title="Italian Student Document Assistant",
        page_icon="🇮🇹",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS for better UI
    st.markdown("""
    <style>
    .main > div {
        padding-top: 1rem;
    }
    .stChatMessage {
        margin-bottom: 1rem;
    }
    .stButton > button {
        width: 100%;
    }
    .stSelectbox > div > div {
        background-color: #f0f2f6;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
    }
    /* Sidebar scrollable area */
    .css-1d391kg {
        max-height: 70vh;
        overflow-y: auto;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Validate configuration
    if not validate_config():
        st.error("❌ Configuration validation failed. Please check your environment variables.")
        return
    
    # Initialize session state
    initialize_simple_session_state()
    
    # Check if user is logged in
    if 'user' not in st.session_state:
        # Show authentication interface
        render_auth_section()
        return
    
    # User is logged in - show main app
    render_chat_sidebar()
    render_header()
    render_document_upload()
    render_chat_interface()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 1rem;">
        Made for international students in Italy 🇮🇹
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()