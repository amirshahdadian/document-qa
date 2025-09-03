import pytest
from unittest.mock import Mock, patch, MagicMock
from app.pdf_processing import PDFProcessor
from app.qa_pipeline import QAPipeline
from langchain.schema import Document

class TestIntegration:
    
    @patch('app.qa_pipeline.GoogleGenerativeAIEmbeddings')
    @patch('app.pdf_processing.PyPDFLoader')
    @patch('langchain_community.vectorstores.Chroma')
    @patch('app.qa_pipeline.ChatGoogleGenerativeAI')
    @patch('langchain.chains.RetrievalQA')
    @patch('tempfile.NamedTemporaryFile')
    @patch('os.unlink')
    def test_full_pdf_qa_pipeline(self, mock_unlink, mock_tempfile, mock_retrieval_qa, 
                                 mock_chat_ai, mock_chroma, mock_loader, mock_embeddings, mock_env_vars):
        """Test complete pipeline: PDF upload → processing → Q&A."""
        
        # Setup file mock
        mock_temp = Mock()
        mock_temp.name = "/tmp/test.pdf"
        mock_tempfile.return_value.__enter__.return_value = mock_temp
        
        # Setup document mock
        mock_documents = [Document(page_content="AI is artificial intelligence.", metadata={"page": 1})]
        mock_loader.return_value.load.return_value = mock_documents
        
        # Setup embeddings mock
        mock_embeddings_instance = Mock()
        mock_embeddings.return_value = mock_embeddings_instance
        
        # Setup vector store mock
        mock_vector_store = Mock()
        mock_chroma.from_documents.return_value = mock_vector_store
        
        # Setup QA chain mock
        mock_qa_chain = Mock()
        mock_qa_chain.invoke.return_value = {
            "result": "AI stands for Artificial Intelligence",
            "source_documents": mock_documents
        }
        mock_retrieval_qa.from_chain_type.return_value = mock_qa_chain
        
        # Create components
        pdf_processor = PDFProcessor()
        qa_pipeline = QAPipeline()
        
        # Create mock PDF file
        mock_pdf_file = Mock()
        mock_pdf_file.name = "test.pdf"
        mock_pdf_file.size = 1024
        mock_pdf_file.getvalue.return_value = b"mock pdf content"
        
        # Test the pipeline
        chunks = pdf_processor.load_and_process_pdf(mock_pdf_file)
        
        # Mock create_vector_store to return mock vector store
        with patch.object(qa_pipeline, 'create_vector_store', return_value=mock_vector_store):
            vector_store = qa_pipeline.create_vector_store(chunks, "test_user", "test_session")
        
        # Mock setup_qa_chain to return mock QA chain
        with patch.object(qa_pipeline, 'setup_qa_chain', return_value=mock_qa_chain):
            qa_chain = qa_pipeline.setup_qa_chain(vector_store)
        
        # Test ask_question
        result = qa_pipeline.ask_question(qa_chain, "What is AI?")
        
        # Validate results
        assert len(chunks) > 0
        assert vector_store is not None
        assert qa_chain is not None
        assert result['question'] == "What is AI?"
        assert 'answer' in result
        assert result['sources_count'] > 0