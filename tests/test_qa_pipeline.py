import pytest
from unittest.mock import Mock, patch
from app.qa_pipeline import QAPipeline

class TestQAPipeline:
    
    @patch('app.qa_pipeline.GoogleGenerativeAIEmbeddings')
    def test_init(self, mock_embeddings, mock_env_vars):
        """Test QA pipeline initialization."""
        qa_pipeline = QAPipeline()
        assert qa_pipeline.embeddings is not None
        mock_embeddings.assert_called_once()
    
    def test_create_vector_store_empty_chunks(self, mock_env_vars):
        """Test vector store creation with empty chunks raises ValueError."""
        qa_pipeline = QAPipeline()
        with pytest.raises(ValueError, match="No document chunks provided"):
            qa_pipeline.create_vector_store([], "test_user", "test_session")
    
    def test_ask_question_empty_question(self, mock_env_vars):
        """Test asking an empty question raises ValueError."""
        qa_pipeline = QAPipeline()
        mock_qa_chain = Mock()
        
        with pytest.raises(ValueError, match="Question cannot be empty"):
            qa_pipeline.ask_question(mock_qa_chain, "")