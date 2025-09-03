import pytest
import os
from unittest.mock import patch
from app.config import validate_config

class TestConfig:
    
    def test_validate_config_success(self, mock_env_vars):
        """Test successful configuration validation."""
        # Reset the global validation state before testing
        import app.config
        app.config._config_validated = False
        
        result = validate_config()
        assert result is True
    
    def test_validate_config_missing_vars(self):
        """Test configuration validation with missing variables."""
        # Reset the global validation state before testing
        import app.config
        app.config._config_validated = False
        
        # Clear all environment variables that might be set
        with patch.dict(os.environ, {}, clear=True):
            result = validate_config()
            assert result is False