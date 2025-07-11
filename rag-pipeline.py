import os
from pathlib import Path
import streamlit as st
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain.vectorstores import FAISS
from langchain.chains import RetrievalQA
import tempfile
from dotenv import load_dotenv
import logging

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
            model="gemini-2.5-flash",  # Updated model name
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
    
    st.title("📚 PDF Document Q&A with RAG (Gemini)")
    st.markdown("Upload a PDF document and ask questions about its content!")
    
    # Sidebar with configuration
    with st.sidebar:
        st.header("Configuration")
        
        # Model selection
        model_options = ["gemini-2.5-flash", "gemini-2.5-pro"]
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
                    
                    st.success(f"✅ PDF processed! {len(chunks)} chunks created.")
                    
            except Exception as e:
                st.error(f"❌ Error processing PDF: {str(e)}")
    
    # Question input and chat interface
    if st.session_state.qa_chain is not None:
        st.markdown("---")
        st.header("💬 Ask Questions")
        
        # Display chat history
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
        
        col1, col2 = st.columns([1, 4])
        with col1:
            ask_button = st.button("🚀 Ask", type="primary")
        with col2:
            if st.button("🗑️ Clear History"):
                st.session_state.chat_history = []
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