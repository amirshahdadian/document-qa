import os
from pathlib import Path
import streamlit as st
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS  # Fixed deprecated import
from langchain.chains import RetrievalQA
import tempfile
from dotenv import load_dotenv
import logging
from firebase_auth import FirebaseAuth

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

def load_and_process_pdf(pdf_file):
    """Load and process PDF file into chunks"""
    try:
        # Validate file size (limit to 50MB)
        if pdf_file.size > 50 * 1024 * 1024:
            raise ValueError("File size exceeds 50MB limit")
        
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(pdf_file.getvalue())
            tmp_path = tmp_file.name
        
        # Load PDF
        loader = PyPDFLoader(tmp_path)
        documents = loader.load()
        
        if not documents:
            raise ValueError("No content found in PDF")
        
        # Split into chunks with improved parameters
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )
        chunks = text_splitter.split_documents(documents)
        
        # Clean up temp file
        os.unlink(tmp_path)
        
        logger.info(f"Successfully processed PDF: {len(chunks)} chunks created")
        return chunks
        
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        if 'tmp_path' in locals():
            try:
                os.unlink(tmp_path)
            except:
                pass
        raise e

def create_vector_store(_chunks):
    """Create vector store from document chunks - note the underscore prefix to avoid caching"""
    try:
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        vector_store = FAISS.from_documents(_chunks, embeddings)
        return vector_store
    except Exception as e:
        logger.error(f"Error creating vector store: {str(e)}")
        raise e

def setup_qa_chain(vector_store):
    """Setup the question-answering chain with improved parameters"""
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",  # Fixed model name
            temperature=0.1,
            max_tokens=1000
        )
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=vector_store.as_retriever(
                search_type="mmr",  # Maximum Marginal Relevance
                search_kwargs={"k": 5, "fetch_k": 10}
            ),
            return_source_documents=True
        )
        return qa_chain
    except Exception as e:
        logger.error(f"Error setting up QA chain: {str(e)}")
        raise e

def main():
    st.set_page_config(
        page_title="PDF Q&A with RAG",
        page_icon="📚",
        layout="wide"
    )
    
    # Initialize Firebase Auth
    firebase_auth = FirebaseAuth()
    
    # Authentication sidebar
    with st.sidebar:
        st.header("🔐 Authentication")
        
        if 'user' not in st.session_state:
            # Login/Register tabs
            tab1, tab2 = st.tabs(["Login", "Register"])
            
            with tab1:
                with st.form("login_form"):
                    email = st.text_input("Email")
                    password = st.text_input("Password", type="password")
                    if st.form_submit_button("Login"):
                        user_data = firebase_auth.login(email, password)
                        if user_data:
                            st.session_state.user = user_data
                            st.success("Logged in successfully!")
                            st.rerun()
                        else:
                            st.error("Invalid credentials")
            
            with tab2:
                with st.form("register_form"):
                    email = st.text_input("Email")
                    password = st.text_input("Password", type="password")
                    display_name = st.text_input("Display Name")
                    if st.form_submit_button("Register"):
                        user_data = firebase_auth.register(email, password, display_name)
                        if user_data:
                            st.session_state.user = user_data
                            st.success("Registered successfully!")
                            st.rerun()
                        else:
                            st.error("Registration failed")
        else:
            # User is logged in
            user_email = st.session_state.user.get('email', 'User')
            st.success(f"Welcome {user_email}")
            if st.button("Logout"):
                firebase_auth.logout()
                st.rerun()
            
            # User's document history
            st.markdown("---")
            st.subheader("📁 Your Documents")
            user_id = st.session_state.user.get('localId')
            if user_id:
                documents = firebase_auth.get_user_documents(user_id)
                if documents:
                    for doc in documents[:5]:  # Show last 5 documents
                        st.text(f"📄 {doc['filename']} ({doc['file_size']} bytes)")
                else:
                    st.info("No documents uploaded yet")
            
            # Add Previous Chat Sessions section
            st.markdown("---")
            st.subheader("💬 Previous Chat Sessions")
            if user_id:
                try:
                    chat_sessions = firebase_auth.get_chat_history(user_id, limit=10)
                    if chat_sessions:
                        session_options = {}
                        for session in chat_sessions:
                            session_timestamp = session.get('session_timestamp')
                            message_count = session.get('message_count', 0)
                            session_id = session.get('id')
                            
                            # Format session display name
                            if hasattr(session_timestamp, 'strftime'):
                                time_str = session_timestamp.strftime("%m/%d %H:%M")
                            else:
                                time_str = "Unknown time"
                            
                            display_name = f"{time_str} ({message_count} msgs)"
                            session_options[display_name] = session
                        
                        # Add option for new session
                        session_options["📝 New Session"] = None
                        
                        # Session selector
                        selected_session_name = st.selectbox(
                            "Select Session:",
                            options=list(session_options.keys()),
                            key="session_selector"
                        )
                        
                        selected_session = session_options[selected_session_name]
                        
                        # Load selected session
                        if selected_session and st.button("📖 Load Session"):
                            # Convert saved format back to chat_history format
                            saved_history = selected_session.get('chat_history', [])
                            if saved_history and isinstance(saved_history[0], dict):
                                # Convert from dict format to tuple format
                                st.session_state.chat_history = [
                                    (item['question'], item['answer']) 
                                    for item in saved_history
                                ]
                            else:
                                st.session_state.chat_history = saved_history
                                
                            st.session_state.current_session_id = selected_session.get('id')
                            st.success("Session loaded!")
                            st.rerun()
                        
                        # Start new session
                        if selected_session_name == "📝 New Session" and st.button("🆕 New Session"):
                            st.session_state.chat_history = []
                            if 'current_session_id' in st.session_state:
                                del st.session_state.current_session_id
                            st.success("New session started!")
                            st.rerun()
                    else:
                        st.info("No previous sessions found")
                except Exception as e:
                    st.error(f"Error loading chat sessions: {str(e)}")
                    st.info("No previous sessions found")
    
    # Main app content
    if 'user' not in st.session_state:
        st.title("📚 PDF Document Q&A with RAG")
        st.warning("🔒 Please login to access the PDF Q&A system")
        st.markdown("This app uses Google's Gemini AI to answer questions about your PDF documents using RAG (Retrieval Augmented Generation).")
        return
    
    # User is authenticated - show main app
    st.title("📚 PDF Document Q&A with RAG (Gemini)")
    st.markdown("Upload a PDF document and ask questions about its content!")
    
    # Show current session info
    user_id = st.session_state.user.get('localId')
    if 'current_session_id' in st.session_state:
        st.info(f"📋 Current Session: {st.session_state.current_session_id}")
    else:
        st.info("📋 Current Session: New (not saved)")
    
    # Configuration sidebar
    with st.sidebar:
        st.markdown("---")
        st.header("⚙️ Configuration")
        
        # Model selection
        model_options = ["gemini-2.5-flash", "gemini-2.5-pro"]  # Fixed model names
        selected_model = st.selectbox("Select Model:", model_options)
        
        # Temperature setting
        temperature = st.slider("Temperature:", 0.0, 1.0, 0.1, 0.1)
        
        # Number of retrieved documents
        k_docs = st.slider("Number of retrieved documents:", 1, 10, 5)
        
        st.markdown("---")
        st.markdown("### About")
        st.markdown("This app uses Google's Gemini AI to answer questions about your PDF documents using RAG (Retrieval Augmented Generation).")
    
    # Check for Google API key
    if not os.getenv("GOOGLE_API_KEY"):
        st.error("❌ Please set your GOOGLE_API_KEY environment variable")
        st.info("Add your API key to the .env file: `GOOGLE_API_KEY=your_key_here`")
        return
    
    # File upload with better UI
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Upload a PDF file", 
            type="pdf",
            help="Maximum file size: 50MB"
        )
    
    with col2:
        if uploaded_file:
            st.info(f"📄 File: {uploaded_file.name}")
            st.info(f"📊 Size: {uploaded_file.size / 1024:.1f} KB")
    
    # Initialize session state
    if "vector_store" not in st.session_state:
        st.session_state.vector_store = None
    if "qa_chain" not in st.session_state:
        st.session_state.qa_chain = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    if uploaded_file is not None:
        # Process PDF button
        if st.button("🔄 Process PDF", type="primary"):
            try:
                with st.spinner("Processing PDF..."):
                    # Process PDF
                    chunks = load_and_process_pdf(uploaded_file)
                    
                    # Create vector store (without caching to avoid hashing issues)
                    st.session_state.vector_store = create_vector_store(chunks)
                    
                    # Setup QA chain with current settings
                    llm = ChatGoogleGenerativeAI(
                        model=selected_model,
                        temperature=temperature,
                        max_tokens=1000
                    )
                    st.session_state.qa_chain = RetrievalQA.from_chain_type(
                        llm=llm,
                        chain_type="stuff",
                        retriever=st.session_state.vector_store.as_retriever(
                            search_type="mmr",
                            search_kwargs={"k": k_docs, "fetch_k": k_docs * 2}
                        ),
                        return_source_documents=True
                    )
                    
                    # Save document metadata to Firebase
                    user_id = st.session_state.user.get('localId')
                    if user_id:
                        firebase_auth.save_document_metadata(
                            user_id, 
                            uploaded_file.name, 
                            uploaded_file.size, 
                            len(chunks)
                        )
                    
                    st.success(f"✅ PDF processed! {len(chunks)} chunks created.")
                    
            except Exception as e:
                st.error(f"❌ Error processing PDF: {str(e)}")
    
    # Question input and chat interface
    if st.session_state.qa_chain is not None:
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
                user_id = st.session_state.user.get('localId')
                if user_id and st.session_state.chat_history:
                    session_id = firebase_auth.save_chat_history(user_id, st.session_state.chat_history)
                    if session_id:
                        st.session_state.current_session_id = session_id
                        st.success("Session saved!")
                    else:
                        st.error("Failed to save session")
        with col4:
            if st.button("🔄 Refresh Sessions"):
                st.rerun()
        
        if question and ask_button:
            try:
                with st.spinner("🔍 Searching for answer..."):
                    result = st.session_state.qa_chain({"query": question})
                    
                    # Add to chat history
                    st.session_state.chat_history.append((question, result["result"]))
                    
                    # Display current answer
                    st.markdown("### 💡 Answer:")
                    st.markdown(result["result"])
                    
                    # Show source documents
                    if result.get("source_documents"):
                        with st.expander("📖 Source Documents"):
                            for i, doc in enumerate(result["source_documents"]):
                                st.markdown(f"**Source {i+1}:**")
                                st.text_area(
                                    f"Content {i+1}:",
                                    doc.page_content[:500] + "..." if len(doc.page_content) > 500 else doc.page_content,
                                    height=100,
                                    key=f"source_{i}_{len(st.session_state.chat_history)}"
                                )
                                if hasattr(doc, 'metadata') and doc.metadata:
                                    st.json(doc.metadata)
                                st.markdown("---")
                    
                    st.rerun()
                    
            except Exception as e:
                st.error(f"❌ Error generating answer: {str(e)}")
    
    else:
        st.info("👆 Please upload and process a PDF file first.")

if __name__ == "__main__":
    main()