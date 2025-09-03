import logging
import hashlib
import os
import tempfile
import shutil
from typing import List, Dict, Any, Optional
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain.chains import RetrievalQA
from langchain.schema import Document
from app.config import (
    DEFAULT_MODEL, DEFAULT_TEMPERATURE,
    DEFAULT_K_DOCS, DEFAULT_FETCH_K, SEARCH_TYPE,
    CHROMA_PERSIST_DIRECTORY, CHROMA_COLLECTION_PREFIX,
    IS_PRODUCTION
)
from app.gcs_storage import GCSStorage
import chromadb

# Set logger level based on environment
logger = logging.getLogger(__name__)
if IS_PRODUCTION:
    logger.setLevel(logging.ERROR)

class QAPipeline:
    def __init__(self):
        self.embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        self.gcs_storage = GCSStorage()
        # Initialize ChromaDB client with proper persistence settings
        self.chroma_client = chromadb.PersistentClient(
            path=CHROMA_PERSIST_DIRECTORY,
            settings=chromadb.Settings(
                persist_directory=CHROMA_PERSIST_DIRECTORY,
                is_persistent=True
            )
        )
    
    def generate_collection_name(self, user_id: str, session_id: str) -> str:
        """Generate a unique collection name for user session."""
        safe_user_id = hashlib.md5(user_id.encode()).hexdigest()[:8]
        safe_session_id = hashlib.md5(session_id.encode()).hexdigest()[:8]
        collection_name = f"{CHROMA_COLLECTION_PREFIX}_{safe_user_id}_{safe_session_id}"
        return collection_name
    
    def _get_collection_local_path(self, user_id: str, session_id: str) -> str:
        """Get local path for collection storage."""
        collection_name = self.generate_collection_name(user_id, session_id)
        return os.path.join(CHROMA_PERSIST_DIRECTORY, collection_name)
    
    def create_vector_store(self, chunks: List[Document], user_id: str, session_id: str) -> Chroma:
        """Create and persist vector store from document chunks with GCS backup."""
        try:
            if not chunks:
                raise ValueError("No document chunks provided")
            
            collection_name = self.generate_collection_name(user_id, session_id)
            
            # Check if collection already exists and delete it to recreate
            try:
                existing_collection = self.chroma_client.get_collection(collection_name)
                self.chroma_client.delete_collection(collection_name)
                if not IS_PRODUCTION:
                    logger.info(f"Deleted existing collection '{collection_name}' for recreation")
            except Exception:
                pass  # Collection doesn't exist, which is fine
            
            # Create ChromaDB vector store with persistence
            vector_store = Chroma.from_documents(
                documents=chunks,
                embedding=self.embeddings,
                collection_name=collection_name,
                persist_directory=CHROMA_PERSIST_DIRECTORY,
                client=self.chroma_client
            )
            
            # Verify the collection was created and has data
            collection = self.chroma_client.get_collection(collection_name)
            doc_count = collection.count()
            
            if not IS_PRODUCTION:
                logger.info(f"Created and persisted vector store '{collection_name}' with {doc_count} documents")
            
            if doc_count == 0:
                raise ValueError(f"Vector store was created but contains no documents")
            
            # Upload to GCS for persistence across deployments
            collection_local_path = self._get_collection_local_path(user_id, session_id)
            if os.path.exists(collection_local_path):
                self.gcs_storage.upload_chroma_collection(collection_local_path, user_id, session_id)
                logger.info(f"Uploaded vector store to GCS for user {user_id}, session {session_id}")
            
            return vector_store
        except Exception as e:
            logger.error(f"Error creating vector store: {str(e)}")
            raise e
    
    def load_vector_store(self, user_id: str, session_id: str) -> Optional[Chroma]:
        """Load existing vector store for a user session, downloading from GCS if needed."""
        try:
            collection_name = self.generate_collection_name(user_id, session_id)
            collection_local_path = self._get_collection_local_path(user_id, session_id)
            
            # First, try to load from local storage
            try:
                collection = self.chroma_client.get_collection(collection_name)
                doc_count = collection.count()
                
                if doc_count > 0:
                    # Local collection exists and has data
                    vector_store = Chroma(
                        collection_name=collection_name,
                        embedding_function=self.embeddings,
                        persist_directory=CHROMA_PERSIST_DIRECTORY,
                        client=self.chroma_client
                    )
                    
                    # Verify the vector store is functional
                    test_results = vector_store.similarity_search("test", k=1)
                    
                    if not IS_PRODUCTION:
                        logger.info(f"Loaded existing local vector store '{collection_name}' with {doc_count} documents")
                    return vector_store
                
            except Exception as e:
                if not IS_PRODUCTION:
                    logger.info(f"Local collection '{collection_name}' not found or empty: {e}")
            
            # If local doesn't exist or is empty, try to download from GCS
            if self.gcs_storage.collection_exists(user_id, session_id):
                logger.info(f"Downloading vector store from GCS for user {user_id}, session {session_id}")
                
                # Download collection from GCS
                if self.gcs_storage.download_chroma_collection(collection_local_path, user_id, session_id):
                    # Try to load the downloaded collection
                    try:
                        vector_store = Chroma(
                            collection_name=collection_name,
                            embedding_function=self.embeddings,
                            persist_directory=CHROMA_PERSIST_DIRECTORY,
                            client=self.chroma_client
                        )
                        
                        # Verify the vector store is functional
                        test_results = vector_store.similarity_search("test", k=1)
                        
                        collection = self.chroma_client.get_collection(collection_name)
                        doc_count = collection.count()
                        
                        logger.info(f"Successfully loaded vector store from GCS '{collection_name}' with {doc_count} documents")
                        return vector_store
                        
                    except Exception as e:
                        logger.error(f"Failed to load downloaded collection: {e}")
                        # Clean up corrupted download
                        if os.path.exists(collection_local_path):
                            shutil.rmtree(collection_local_path)
                        return None
                else:
                    logger.warning(f"Failed to download collection from GCS for user {user_id}, session {session_id}")
                    return None
            else:
                if not IS_PRODUCTION:
                    logger.info(f"No vector store found in GCS for user {user_id}, session {session_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error loading vector store: {str(e)}")
            return None
    
    def delete_vector_store(self, user_id: str, session_id: str) -> bool:
        """Delete vector store both locally and from GCS."""
        try:
            collection_name = self.generate_collection_name(user_id, session_id)
            collection_local_path = self._get_collection_local_path(user_id, session_id)
            
            success = True
            
            # Delete from local ChromaDB
            try:
                self.chroma_client.delete_collection(collection_name)
                if not IS_PRODUCTION:
                    logger.info(f"Deleted local vector store '{collection_name}'")
            except Exception as e:
                if not IS_PRODUCTION:
                    logger.warning(f"Failed to delete local collection '{collection_name}': {e}")
                success = False
            
            # Delete local files
            if os.path.exists(collection_local_path):
                try:
                    shutil.rmtree(collection_local_path)
                    if not IS_PRODUCTION:
                        logger.info(f"Deleted local collection files: {collection_local_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete local files: {e}")
            
            # Delete from GCS
            if not self.gcs_storage.delete_chroma_collection(user_id, session_id):
                success = False
            
            return success
        except Exception as e:
            logger.error(f"Error deleting vector store: {str(e)}")
            return False
    
    def list_collections(self) -> List[str]:
        """List all available collections for debugging."""
        try:
            collections = self.chroma_client.list_collections()
            return [col.name for col in collections]
        except Exception as e:
            logger.error(f"Error listing collections: {e}")
            return []
    
    def setup_qa_chain(self, vector_store: Chroma) -> RetrievalQA:
        """Setup the question-answering chain with default settings."""
        try:
            llm = ChatGoogleGenerativeAI(
                model=DEFAULT_MODEL,
                temperature=DEFAULT_TEMPERATURE
            )
            
            retriever = vector_store.as_retriever(
                search_type=SEARCH_TYPE,
                search_kwargs={"k": DEFAULT_K_DOCS}
            )
            
            qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=retriever,
                return_source_documents=True
            )
            
            if not IS_PRODUCTION:
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
            
            if not IS_PRODUCTION:
                logger.info(f"Question answered successfully: {question[:50]}...")
            return response
        except Exception as e:
            logger.error(f"Error answering question: {str(e)}")
            raise e
    
    def get_collection_info(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """Get information about the vector store collection."""
        try:
            collection_name = self.generate_collection_name(user_id, session_id)
            
            # Check local collection
            local_exists = False
            local_count = 0
            try:
                collection = self.chroma_client.get_collection(collection_name)
                local_count = collection.count()
                local_exists = True
            except Exception:
                pass
            
            # Check GCS collection
            gcs_exists = self.gcs_storage.collection_exists(user_id, session_id)
            
            return {
                "exists": local_exists or gcs_exists,
                "name": collection_name,
                "count": local_count,
                "local_exists": local_exists,
                "gcs_exists": gcs_exists,
                "metadata": {}
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {str(e)}")
            return {"exists": False, "error": str(e)}
    
    def get_similar_documents(self, vector_store: Chroma, query: str, k: int = 3) -> List[Document]:
        """Get similar documents for testing purposes."""
        try:
            return vector_store.similarity_search(query, k=k)
        except Exception as e:
            logger.error(f"Error getting similar documents: {str(e)}")
            return []
