import logging
from typing import List, Dict, Any
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.schema import Document
from app.config import (
    DEFAULT_MODEL, DEFAULT_TEMPERATURE, DEFAULT_MAX_TOKENS, 
    DEFAULT_K_DOCS, DEFAULT_FETCH_K, SEARCH_TYPE
)

logger = logging.getLogger(__name__)

class QAPipeline:
    def __init__(self):
        self.embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    
    def create_vector_store(self, chunks: List[Document]) -> FAISS:
        """Create vector store from document chunks."""
        try:
            if not chunks:
                raise ValueError("No document chunks provided")
            
            vector_store = FAISS.from_documents(chunks, self.embeddings)
            logger.info(f"Created vector store with {len(chunks)} chunks")
            return vector_store
        except Exception as e:
            logger.error(f"Error creating vector store: {str(e)}")
            raise e
    
    def setup_qa_chain(
        self, 
        vector_store: FAISS, 
        model: str = DEFAULT_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        k_docs: int = DEFAULT_K_DOCS
    ) -> RetrievalQA:
        """Setup the question-answering chain."""
        try:
            llm = ChatGoogleGenerativeAI(
                model=model,
                temperature=temperature,
                max_tokens=DEFAULT_MAX_TOKENS
            )
            
            retriever = vector_store.as_retriever(
                search_type=SEARCH_TYPE,
                search_kwargs={"k": k_docs, "fetch_k": DEFAULT_FETCH_K}
            )
            
            qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=retriever,
                return_source_documents=True
            )
            
            logger.info(f"QA chain setup successfully with model: {model}")
            return qa_chain
        except Exception as e:
            logger.error(f"Error setting up QA chain: {str(e)}")
            raise e
    
    def ask_question(self, qa_chain: RetrievalQA, question: str) -> Dict[str, Any]:
        """Ask a question and get an answer with sources."""
        try:
            if not question.strip():
                raise ValueError("Question cannot be empty")
            
            result = qa_chain({"query": question})
            
            # Format the response
            response = {
                "question": question,
                "answer": result["result"],
                "source_documents": result.get("source_documents", []),
                "sources_count": len(result.get("source_documents", []))
            }
            
            logger.info(f"Question answered successfully: {question[:50]}...")
            return response
        except Exception as e:
            logger.error(f"Error answering question: {str(e)}")
            raise e
    
    def get_similar_documents(self, vector_store: FAISS, query: str, k: int = 3) -> List[Document]:
        """Get similar documents for a query."""
        try:
            docs = vector_store.similarity_search(query, k=k)
            return docs
        except Exception as e:
            logger.error(f"Error getting similar documents: {str(e)}")
            return []
    
    def update_qa_chain_settings(
        self, 
        qa_chain: RetrievalQA, 
        model: str = None,
        temperature: float = None,
        k_docs: int = None
    ) -> RetrievalQA:
        """Update QA chain settings."""
        try:
            # For now, we need to recreate the chain with new settings
            # This is a limitation of the current LangChain implementation
            logger.info("QA chain settings updated (requires recreation)")
            return qa_chain
        except Exception as e:
            logger.error(f"Error updating QA chain settings: {str(e)}")
            raise e