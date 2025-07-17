import pytest
from unittest.mock import Mock, patch
from app.pdf_processing import PDFProcessor

class TestPDFProcessor:
    
    def test_validate_file_success(self, mock_pdf_file):
        """Test successful file validation."""
        processor = PDFProcessor()
        assert processor.validate_file(mock_pdf_file) is True
    
    def test_validate_file_size_limit(self):
        """Test file size validation fails for large files."""
        processor = PDFProcessor()
        mock_file = Mock()
        mock_file.name = "large.pdf"
        mock_file.size = 100 * 1024 * 1024  # 100MB - exceeds limit
        
        with pytest.raises(ValueError, match="File size exceeds"):
            processor.validate_file(mock_file)
    
    def test_validate_file_wrong_type(self):
        """Test file type validation fails for non-PDF files."""
        processor = PDFProcessor()
        mock_file = Mock()
        mock_file.name = "document.txt"
        mock_file.size = 1024
        
        with pytest.raises(ValueError, match="Only PDF files are supported"):
            processor.validate_file(mock_file)