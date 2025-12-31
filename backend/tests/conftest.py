"""Pytest configuration and fixtures."""
import os
import sys
from pathlib import Path

import pytest

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set test environment variables before importing app modules
os.environ["DATA_DIR"] = str(Path(__file__).parent / "test_data")
os.environ["LOG_FILE"] = str(Path(__file__).parent / "test_data" / "logs" / "app.jsonl")
os.environ["ALLOW_NON_LOCALHOST"] = "true"


@pytest.fixture
def temp_data_dir(tmp_path: Path) -> Path:
    """Create a temporary data directory for tests."""
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "sessions").mkdir(parents=True, exist_ok=True)
    (data_dir / "logs").mkdir(parents=True, exist_ok=True)
    return data_dir


@pytest.fixture
def session_id() -> str:
    """Provide a test session ID."""
    return "12345678-1234-1234-1234-123456789abc"
