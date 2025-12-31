"""Unit tests for configuration."""
import pytest
from pathlib import Path
import os

from app.config import Settings


class TestConfiguration:
    """Tests for application configuration."""

    def test_default_host_and_port(self) -> None:
        """Test default host and port values."""
        settings = Settings(_env_file=None)
        
        assert settings.HOST == "127.0.0.1"
        assert settings.PORT == 5000

    def test_default_session_limits(self) -> None:
        """Test default session limit values."""
        settings = Settings(_env_file=None)
        
        assert settings.MAX_SESSIONS == 10
        assert settings.MAX_INPUT_CHARS_PER_MESSAGE == 16384
        assert settings.WS_MAX_MESSAGE_BYTES == 1048576

    def test_default_terminal_dimensions(self) -> None:
        """Test default terminal dimension values."""
        settings = Settings(_env_file=None)
        
        assert settings.INITIAL_COLS == 120
        assert settings.INITIAL_ROWS == 30
        assert settings.MIN_COLS == 20
        assert settings.MAX_COLS == 300
        assert settings.MIN_ROWS == 5
        assert settings.MAX_ROWS == 120

    def test_sessions_dir_property(self) -> None:
        """Test sessions_dir property."""
        settings = Settings(_env_file=None)
        
        assert settings.sessions_dir == settings.DATA_DIR / "sessions"

    def test_logs_dir_property(self) -> None:
        """Test logs_dir property."""
        settings = Settings(_env_file=None)
        
        assert settings.logs_dir == settings.DATA_DIR / "logs"

    def test_validate_localhost_binding_allowed(self) -> None:
        """Test that localhost binding is allowed."""
        settings = Settings(HOST="127.0.0.1", _env_file=None)
        
        # Should not raise
        settings.validate_localhost_binding()

    def test_validate_localhost_binding_rejected(self) -> None:
        """Test that non-localhost binding is rejected."""
        settings = Settings(HOST="0.0.0.0", ALLOW_NON_LOCALHOST=False, _env_file=None)
        
        with pytest.raises(ValueError, match="127.0.0.1"):
            settings.validate_localhost_binding()

    def test_validate_non_localhost_when_allowed(self) -> None:
        """Test that non-localhost binding is allowed when configured."""
        settings = Settings(HOST="0.0.0.0", ALLOW_NON_LOCALHOST=True, _env_file=None)
        
        # Should not raise
        settings.validate_localhost_binding()

    def test_path_conversion(self) -> None:
        """Test that string paths are converted to Path objects."""
        settings = Settings(DATA_DIR="./test_data", _env_file=None)
        
        assert isinstance(settings.DATA_DIR, Path)
