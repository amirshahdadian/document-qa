import pytest
import os
from unittest.mock import Mock, patch

@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing."""
    with patch.dict(os.environ, {
        'GOOGLE_API_KEY': 'test_key',
        'FIREBASE_API_KEY': 'test_firebase_key',
        'FIREBASE_AUTH_DOMAIN': 'test.firebaseapp.com',
        'FIREBASE_PROJECT_ID': 'test-project',
        'FIREBASE_STORAGE_BUCKET': 'test.appspot.com',
        'FIREBASE_MESSAGING_SENDER_ID': '123456789',
        'FIREBASE_APP_ID': '1:123456789:web:abcdef',
        'FIREBASE_SERVICE_ACCOUNT_KEY': 'dGVzdA=='  # base64 encoded 'test'
    }):
        yield

@pytest.fixture
def mock_pdf_file():
    """Create a mock PDF file for testing."""
    mock_file = Mock()
    mock_file.name = "test.pdf"
    mock_file.size = 1024 * 1024  # 1MB
    mock_file.getvalue.return_value = b"mock pdf content"
    return mock_file