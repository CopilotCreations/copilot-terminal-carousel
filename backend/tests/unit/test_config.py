"""Unit tests for configuration."""
import pytest
from pathlib import Path
import os

from app.config import Settings


class TestConfiguration:
    """Tests for application configuration."""

    def test_default_host_and_port(self) -> None:
        """Test default host and port values.

        Verifies that Settings uses the expected default values for HOST
        and PORT when no environment file is provided.
        """
        settings = Settings(_env_file=None)
        
        assert settings.HOST == "127.0.0.1"
        assert settings.PORT == 5000

    def test_default_session_limits(self) -> None:
        """Test default session limit values.

        Verifies that Settings uses the expected default values for session
        limits including max sessions, input character limits, and WebSocket
        message size limits.
        """
        settings = Settings(_env_file=None)
        
        assert settings.MAX_SESSIONS == 10
        assert settings.MAX_INPUT_CHARS_PER_MESSAGE == 16384
        assert settings.WS_MAX_MESSAGE_BYTES == 1048576

    def test_default_terminal_dimensions(self) -> None:
        """Test default terminal dimension values.

        Verifies that Settings uses the expected default values for terminal
        dimensions including initial, minimum, and maximum columns and rows.
        """
        settings = Settings(_env_file=None)
        
        assert settings.INITIAL_COLS == 120
        assert settings.INITIAL_ROWS == 30
        assert settings.MIN_COLS == 20
        assert settings.MAX_COLS == 300
        assert settings.MIN_ROWS == 5
        assert settings.MAX_ROWS == 120

    def test_sessions_dir_property(self) -> None:
        """Test sessions_dir property.

        Verifies that the sessions_dir property correctly returns the path
        to the sessions subdirectory within DATA_DIR.
        """
        settings = Settings(_env_file=None)
        
        assert settings.sessions_dir == settings.DATA_DIR / "sessions"

    def test_logs_dir_property(self) -> None:
        """Test logs_dir property.

        Verifies that the logs_dir property correctly returns the path
        to the logs subdirectory within DATA_DIR.
        """
        settings = Settings(_env_file=None)
        
        assert settings.logs_dir == settings.DATA_DIR / "logs"

    def test_validate_localhost_binding_allowed(self) -> None:
        """Test that localhost binding is allowed.

        Verifies that validate_localhost_binding does not raise an exception
        when HOST is set to 127.0.0.1 (localhost).
        """
        settings = Settings(HOST="127.0.0.1", _env_file=None)
        
        # Should not raise
        settings.validate_localhost_binding()

    def test_validate_localhost_binding_rejected(self) -> None:
        """Test that non-localhost binding is rejected.

        Verifies that validate_localhost_binding raises a ValueError when
        HOST is not localhost and ALLOW_NON_LOCALHOST is False.

        Raises:
            ValueError: When attempting to bind to non-localhost address
                without explicit permission.
        """
        settings = Settings(HOST="0.0.0.0", ALLOW_NON_LOCALHOST=False, _env_file=None)
        
        with pytest.raises(ValueError, match="127.0.0.1"):
            settings.validate_localhost_binding()

    def test_validate_non_localhost_when_allowed(self) -> None:
        """Test that non-localhost binding is allowed when configured.

        Verifies that validate_localhost_binding does not raise an exception
        when HOST is non-localhost but ALLOW_NON_LOCALHOST is True.
        """
        settings = Settings(HOST="0.0.0.0", ALLOW_NON_LOCALHOST=True, _env_file=None)
        
        # Should not raise
        settings.validate_localhost_binding()

    def test_path_conversion(self) -> None:
        """Test that string paths are converted to Path objects.

        Verifies that Settings correctly converts string path values
        to pathlib.Path objects for the DATA_DIR setting.
        """
        settings = Settings(DATA_DIR="./test_data", _env_file=None)
        
        assert isinstance(settings.DATA_DIR, Path)
