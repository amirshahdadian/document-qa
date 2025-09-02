import streamlit as st
from datetime import datetime
from app.config import validate_config, AVAILABLE_MODELS, DEFAULT_MODEL, GOOGLE_OAUTH_CLIENT_ID, logger, IS_PRODUCTION
from app.auth import AuthService
from app.pdf_processing import PDFProcessor
from app.qa_pipeline import QAPipeline
from app.utils import (
    initialize_session_state, format_file_size, handle_error, 
    show_success, show_info, show_warning, format_timestamp
)
import hashlib
import logging

# Set main logger level
main_logger = logging.getLogger(__name__)
if IS_PRODUCTION:
    main_logger.setLevel(logging.ERROR)

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
    if "processed_auth_codes" not in st.session_state:
        st.session_state.processed_auth_codes = set()
    if "last_processed_code" not in st.session_state:
        st.session_state.last_processed_code = None

def handle_google_oauth_callback():
    """Handle Google OAuth callback."""
    query_params = st.query_params
    
    if "code" in query_params and "state" in query_params:
        if query_params["state"] == "google_auth":
            auth_code = query_params["code"]
            
            # Check if we've already processed this callback
            if 'last_processed_code' in st.session_state and st.session_state.last_processed_code == auth_code:
                # Clear query params and return to avoid reprocessing
                st.query_params.clear()
                return
            
            with st.spinner("🔐 Signing in with Google..."):
                # Exchange code for access token
                access_token = st.session_state.auth_service.exchange_google_code_for_token(auth_code)
                
                if access_token:
                    # Sign in with Firebase using Google token
                    user_data = st.session_state.auth_service.login_with_google(access_token)
                    
                    if user_data:
                        st.session_state.user = user_data
                        st.session_state.last_processed_code = auth_code
                        logger.debug(f"User session state after login: {st.session_state}")
                        st.success("✅ Signed in with Google successfully!")
                        
                        # Clear query parameters
                        st.query_params.clear()
                        st.rerun()
                    else:
                        st.error("❌ Failed to sign in with Google. Please try again.")
                        st.query_params.clear()
                else:
                    st.error("❌ Failed to authenticate with Google. Please try again.")
                    st.query_params.clear()

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
        
        # Google Sign-In Button (if configured)
        if GOOGLE_OAUTH_CLIENT_ID:
            st.markdown("#### 🚀 Quick Sign-In")
            google_oauth_url = st.session_state.auth_service.get_google_oauth_url()
            
            if google_oauth_url:
                st.markdown(f"""
                <div style="text-align: center; margin: 1rem 0;">
                    <a href="{google_oauth_url}" target="_self" style="text-decoration: none;">
                        <button style="
                            background-color: #4285f4;
                            color: white;
                            border: none;
                            padding: 12px 24px;
                            border-radius: 8px;
                            font-size: 16px;
                            font-weight: 500;
                            cursor: pointer;
                            display: inline-flex;
                            align-items: center;
                            gap: 8px;
                            transition: background-color 0.3s;
                        ">
                            <svg width="18" height="18" viewBox="0 0 24 24">
                                <path fill="white" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                                <path fill="white" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                                <path fill="white" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                                <path fill="white" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                            </svg>
                            Continue with Google
                        </button>
                    </a>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown("#### 📧 Or sign in with email")
        
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
    """Load a previous chat session with document embeddings."""
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
                messages.append({"role": "user", "content": item.get('question', '')})
                messages.append({"role": "assistant", "content": item.get('answer', '')})
            else:
                question, answer = item
                messages.append({"role": "user", "content": question})
                messages.append({"role": "assistant", "content": answer})
        
        st.session_state.messages = messages
        
        # Try to load existing document embeddings
        user_id = st.session_state.user.get('localId')
        session_id = st.session_state.current_session_id
        
        if user_id and session_id:
            # Get document info
            doc_info = st.session_state.auth_service.get_session_document_info(user_id, session_id)
            
            # Initialize QA pipeline
            qa_pipeline = QAPipeline()
            
            # Debug: List available collections
            if not IS_PRODUCTION:
                collections = qa_pipeline.list_collections()
                main_logger.info(f"Available collections: {collections}")
                collection_info = qa_pipeline.get_collection_info(user_id, session_id)
                main_logger.info(f"Collection info for session: {collection_info}")
            
            # Try to load vector store regardless of document info
            vector_store = qa_pipeline.load_vector_store(user_id, session_id)
            
            if vector_store:
                # Setup QA chain
                qa_chain = qa_pipeline.setup_qa_chain(vector_store)
                
                # Update session state
                st.session_state.qa_chain = qa_chain
                st.session_state.document_processed = True
                
                # Get document name from doc_info or session data
                document_name = None
                if doc_info:
                    document_name = doc_info.get('filename')
                if not document_name:
                    document_name = session.get('document_name', 'Unknown document')
                
                st.session_state.current_document = document_name
                
                # Add success message
                st.session_state.messages.append({
                    "role": "system",
                    "content": f"📄 **Chat session loaded!** Document **{document_name}** is ready for questions."
                })
                
                show_success(f"Loaded chat session with document: {document_name}")
            else:
                # Vector store not found, clear document state
                st.session_state.qa_chain = None
                st.session_state.document_processed = False
                st.session_state.current_document = None
                
                # Check if we have document metadata but missing embeddings
                if doc_info and doc_info.get('has_embeddings', False):
                    st.session_state.messages.append({
                        "role": "system", 
                        "content": f"📄 **Chat session loaded!** The document embeddings for **{doc_info.get('filename', 'your document')}** were not found. This might happen after app restarts. Please upload the document again to continue asking questions."
                    })
                    show_warning("Chat loaded but document embeddings need to be recreated")
                else:
                    st.session_state.messages.append({
                        "role": "system",
                        "content": "📄 **Chat session loaded!** No document was associated with this session. Upload a document to start asking questions."
                    })
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
            
            # Generate file hash for deduplication
            file_content = uploaded_file.getvalue()
            file_hash = hashlib.sha256(file_content).hexdigest()
            
            # Process PDF
            chunks = pdf_processor.load_and_process_pdf(uploaded_file)
            
            # Get user info
            user_id = st.session_state.user.get('localId')
            session_id = st.session_state.current_session_id
            
            # Create new session if needed
            if not session_id:
                timestamp = datetime.now().strftime("%m/%d %H:%M")
                session_title = f"{uploaded_file.name} - {timestamp}"
                session_id = create_new_session(user_id, session_title, uploaded_file.name)
                st.session_state.current_session_id = session_id
                st.session_state.current_session_title = session_title
            
            # Create and persist vector store
            vector_store = qa_pipeline.create_vector_store(chunks, user_id, session_id)
            
            # Verify the vector store was created properly
            collection_info = qa_pipeline.get_collection_info(user_id, session_id)
            if not collection_info.get('exists') or collection_info.get('count', 0) == 0:
                raise ValueError("Vector store was not created properly")
            
            # Setup QA chain
            qa_chain = qa_pipeline.setup_qa_chain(vector_store)
            
            # Update session state
            st.session_state.qa_chain = qa_chain
            st.session_state.document_processed = True
            st.session_state.current_document = uploaded_file.name
            
            # Save document session info with enhanced metadata
            if user_id and session_id:
                st.session_state.auth_service.save_document_session(
                    user_id, session_id, uploaded_file.name, 
                    uploaded_file.size, len(chunks), file_hash
                )
                
                # Also update the chat session with document info
                from firebase_admin import firestore
                db = firestore.client()
                session_ref = db.collection('users').document(user_id).collection('chat_sessions').document(session_id)
                session_ref.update({
                    'document_name': uploaded_file.name,
                    'updated_at': datetime.now()
                })
            
            # Add system message
            st.session_state.messages.append({
                "role": "system",
                "content": f"Document **{uploaded_file.name}** has been processed and saved! You can now ask questions about it."
            })
            
            show_success("✅ Document processed and saved successfully!")
            
            # Debug info in development
            if not IS_PRODUCTION:
                main_logger.info(f"Document processed: {collection_info}")
            
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
            
            # Update session with retry logic
            for attempt in range(3):
                try:
                    session_ref.update({
                        'chat_history': current_history,
                        'message_count': len(current_history),
                        'updated_at': datetime.now()
                    })
                    # Replace excessive logging
                    if not IS_PRODUCTION:
                        main_logger.info(f"Auto-saved message for session {session_id}")
                    return True
                except Exception as retry_error:
                    logger.warning(f"Retry {attempt + 1}/3 failed for auto-save: {retry_error}")
                    if attempt == 2:
                        raise retry_error
                    
        else:
            logger.warning(f"Session {session_id} not found for auto-save")
            return False
            
    except Exception as e:
        main_logger.error(f"Error auto-saving message: {e}")
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
    
    # Only show quick actions if document is processed
    if st.session_state.document_processed and st.session_state.qa_chain:
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
    elif st.session_state.messages and not st.session_state.document_processed:
        st.info("💡 Upload a document above to activate AI features and quick actions.")
    
    # Chat input - always show but handle appropriately
    if prompt := st.chat_input("Ask a question about your document..."):
        handle_user_input(prompt)

def handle_quick_action(prompt):
    """Handle quick action button clicks."""
    # Check if QA chain is available
    if not st.session_state.qa_chain:
        st.warning("⚠️ Please upload a document first to use quick actions.")
        return
    
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
        # Check if QA chain is available
        if not st.session_state.qa_chain:
            error_message = "⚠️ Please upload a document first to activate the AI assistant. The document needs to be processed before I can answer questions."
            st.session_state.messages.append({
                "role": "assistant",
                "content": error_message
            })
            return
        
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
    """Delete a chat session and its embeddings."""
    try:
        user_id = st.session_state.user.get('localId')
        if user_id:
            # Delete vector store
            qa_pipeline = QAPipeline()
            qa_pipeline.delete_vector_store(user_id, session_id)
            
            # Delete from Firestore
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
    
    # Handle Google OAuth callback
    handle_google_oauth_callback()
    
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