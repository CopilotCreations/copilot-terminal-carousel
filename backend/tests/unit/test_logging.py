"""Unit tests for logging setup."""
import pytest
from pathlib import Path
import os
import logging

from app.logging_setup import setup_logging, get_logger, CustomJsonFormatter


class TestLoggingSetup:
    """Tests for logging setup functionality."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path) -> None:
        """Set up test environment."""
        os.environ["DATA_DIR"] = str(tmp_path / "data")
        os.environ["LOG_FILE"] = str(tmp_path / "data" / "logs" / "app.jsonl")
        os.environ["LOG_LEVEL"] = "DEBUG"
        
        (tmp_path / "data" / "logs").mkdir(parents=True, exist_ok=True)

    def test_get_logger(self) -> None:
        """Test getting a logger."""
        logger = get_logger("test.module")
        
        assert logger is not None
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"

    def test_custom_json_formatter(self) -> None:
        """Test CustomJsonFormatter adds required fields."""
        formatter = CustomJsonFormatter()
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        
        log_record: dict[str, object] = {}
        formatter.add_fields(log_record, record, {})
        
        assert "ts" in log_record
        assert "level" in log_record
        assert "event" in log_record
        assert log_record["level"] == "INFO"
        assert log_record["event"] == "test"
