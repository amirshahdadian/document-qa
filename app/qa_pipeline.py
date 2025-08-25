import logging
from typing import List, Dict, Any
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.schema import Document
from app.config import (
    DEFAULT_MODEL, DEFAULT_TEMPERATURE,
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
    
    def setup_qa_chain(self, vector_store: FAISS) -> RetrievalQA:
        """Setup the question-answering chain with default settings."""
        try:
            llm = ChatGoogleGenerativeAI(
                model=DEFAULT_MODEL,
                temperature=DEFAULT_TEMPERATURE
            )
            
            retriever = vector_store.as_retriever(
                search_type=SEARCH_TYPE,
                search_kwargs={"k": DEFAULT_K_DOCS, "fetch_k": DEFAULT_FETCH_K}
            )
            
            qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=retriever,
                return_source_documents=True
            )
            
            logger.info(f"QA chain setup successfully with model: {DEFAULT_MODEL}")
            return qa_chain
        except Exception as e:
            logger.error(f"Error setting up QA chain: {str(e)}")
            raise e
    
    def ask_question(self, qa_chain: RetrievalQA, question: str) -> Dict[str, Any]:
        """Ask a question and get an answer with sources."""
        try:
            if not question.strip():
                raise ValueError("Question cannot be empty")
            
            result = qa_chain.invoke({"query": question})
            
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