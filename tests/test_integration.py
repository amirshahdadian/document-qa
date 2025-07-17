import pytest
from unittest.mock import Mock, patch
from app.pdf_processing import PDFProcessor
from app.qa_pipeline import QAPipeline
from langchain.schema import Document

class TestIntegration:
    
    @patch('app.pdf_processing.PyPDFLoader')
    @patch('app.qa_pipeline.FAISS')
    @patch('app.qa_pipeline.ChatGoogleGenerativeAI')
    @patch('app.qa_pipeline.RetrievalQA')
    @patch('tempfile.NamedTemporaryFile')
    @patch('os.unlink')
    def test_full_pdf_qa_pipeline(self, mock_unlink, mock_tempfile, mock_retrieval_qa, 
                                 mock_chat_ai, mock_faiss, mock_loader, mock_env_vars):
        """Test complete pipeline: PDF upload → processing → Q&A."""
        
        # Setup mocks
        mock_temp = Mock()
        mock_temp.name = "/tmp/test.pdf"
        mock_tempfile.return_value.__enter__.return_value = mock_temp
        
        mock_documents = [Document(page_content="AI is artificial intelligence.", metadata={"page": 1})]
        mock_loader.return_value.load.return_value = mock_documents
        
        mock_vector_store = Mock()
        mock_faiss.from_documents.return_value = mock_vector_store
        
        mock_qa_chain = Mock()
        mock_qa_chain.return_value = {
            "result": "AI stands for Artificial Intelligence",
            "source_documents": mock_documents
        }
        mock_retrieval_qa.from_chain_type.return_value = mock_qa_chain
        
        # Create components
        pdf_processor = PDFProcessor()
        qa_pipeline = QAPipeline()
        
        # Mock PDF file
        mock_pdf_file = Mock()
        mock_pdf_file.name = "test.pdf"
        mock_pdf_file.size = 1024
        mock_pdf_file.getvalue.return_value = b"mock pdf content"
        
        # Test full pipeline
        chunks = pdf_processor.load_and_process_pdf(mock_pdf_file)
        vector_store = qa_pipeline.create_vector_store(chunks)
        qa_chain = qa_pipeline.setup_qa_chain(vector_store)
        result = qa_pipeline.ask_question(qa_chain, "What is AI?")
        
        # Validate results
        assert len(chunks) > 0
        assert vector_store is not None
        assert qa_chain is not None
        assert result['question'] == "What is AI?"
        assert 'answer' in result
        assert result['sources_count'] > 0