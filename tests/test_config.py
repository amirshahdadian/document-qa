import pytest
from unittest.mock import patch
from app.config import validate_config

class TestConfig:
    
    def test_validate_config_success(self, mock_env_vars):
        """Test successful configuration validation."""
        result = validate_config()
        assert result is True
    
    @patch.dict('os.environ', {}, clear=True)
    def test_validate_config_missing_vars(self):
        """Test configuration validation with missing variables."""
        result = validate_config()
        assert result is False