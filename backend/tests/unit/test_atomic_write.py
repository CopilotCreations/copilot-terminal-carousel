"""Unit tests for atomic write utility."""
import json
import pytest
from pathlib import Path

from app.util.atomic_write import atomic_write_json, read_json_file


class TestAtomicWrite:
    """Tests for atomic write functionality."""

    def test_write_and_read_json(self, tmp_path: Path) -> None:
        """Test writing and reading JSON.

        Args:
            tmp_path: Pytest fixture providing a temporary directory path.
        """
        file_path = tmp_path / "test.json"
        data = {"key": "value", "number": 42}

        atomic_write_json(file_path, data)
        result = read_json_file(file_path)

        assert result == data

    def test_write_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Test that write creates parent directories.

        Args:
            tmp_path: Pytest fixture providing a temporary directory path.
        """
        file_path = tmp_path / "nested" / "dir" / "test.json"
        data = {"test": True}

        atomic_write_json(file_path, data)

        assert file_path.exists()
        result = read_json_file(file_path)
        assert result == data

    def test_write_overwrites_existing(self, tmp_path: Path) -> None:
        """Test that write overwrites existing file.

        Args:
            tmp_path: Pytest fixture providing a temporary directory path.
        """
        file_path = tmp_path / "test.json"

        atomic_write_json(file_path, {"version": 1})
        atomic_write_json(file_path, {"version": 2})

        result = read_json_file(file_path)
        assert result["version"] == 2

    def test_write_complex_data(self, tmp_path: Path) -> None:
        """Test writing complex nested data.

        Args:
            tmp_path: Pytest fixture providing a temporary directory path.
        """
        file_path = tmp_path / "complex.json"
        data = {
            "sessions": [
                {"id": "123", "status": "running"},
                {"id": "456", "status": "exited"},
            ],
            "metadata": {
                "version": 1,
                "updated": "2025-01-01",
            },
        }

        atomic_write_json(file_path, data)
        result = read_json_file(file_path)

        assert result == data
        assert len(result["sessions"]) == 2

    def test_write_unicode(self, tmp_path: Path) -> None:
        """Test writing unicode characters.

        Args:
            tmp_path: Pytest fixture providing a temporary directory path.
        """
        file_path = tmp_path / "unicode.json"
        data = {"message": "Hello, 世界! 🎉"}

        atomic_write_json(file_path, data)
        result = read_json_file(file_path)

        assert result["message"] == "Hello, 世界! 🎉"

    def test_read_nonexistent_raises(self, tmp_path: Path) -> None:
        """Test reading non-existent file raises FileNotFoundError.

        Args:
            tmp_path: Pytest fixture providing a temporary directory path.

        Raises:
            FileNotFoundError: When attempting to read a non-existent file.
        """
        file_path = tmp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError):
            read_json_file(file_path)

    def test_read_invalid_json_raises(self, tmp_path: Path) -> None:
        """Test reading invalid JSON raises JSONDecodeError.

        Args:
            tmp_path: Pytest fixture providing a temporary directory path.

        Raises:
            json.JSONDecodeError: When attempting to read invalid JSON content.
        """
        file_path = tmp_path / "invalid.json"
        file_path.write_text("not valid json {")

        with pytest.raises(json.JSONDecodeError):
            read_json_file(file_path)

    def test_write_produces_valid_json(self, tmp_path: Path) -> None:
        """Test that file contains valid JSON after write.

        Args:
            tmp_path: Pytest fixture providing a temporary directory path.
        """
        file_path = tmp_path / "test.json"
        data = {"test": True}

        atomic_write_json(file_path, data)

        # Read raw file and parse
        content = file_path.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert parsed == data

    def test_no_temp_files_remain(self, tmp_path: Path) -> None:
        """Test that no temporary files remain after write.

        Args:
            tmp_path: Pytest fixture providing a temporary directory path.
        """
        file_path = tmp_path / "test.json"
        data = {"test": True}

        atomic_write_json(file_path, data)

        # Check no temp files in directory
        files = list(tmp_path.iterdir())
        assert len(files) == 1
        assert files[0].name == "test.json"
