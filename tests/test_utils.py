import pytest
from app.utils import format_file_size, format_timestamp, truncate_text
from datetime import datetime

class TestUtils:
    
    def test_format_file_size(self):
        """Test file size formatting."""
        assert format_file_size(0) == "0 B"
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(1024 * 1024) == "1.0 MB"
        assert format_file_size(1024 * 1024 * 1024) == "1.0 GB"
    
    def test_format_timestamp(self):
        """Test timestamp formatting."""
        dt = datetime(2023, 12, 25, 15, 30)
        result = format_timestamp(dt)
        assert result == "12/25/2023 15:30"
        
        result = format_timestamp("invalid")
        assert result == "Unknown time"
    
    def test_truncate_text(self):
        """Test text truncation."""
        long_text = "This is a very long text that should be truncated"
        result = truncate_text(long_text, 20)
        assert result == "This is a very long ..."
        
        short_text = "Short text"
        result = truncate_text(short_text, 20)
        assert result == "Short text"