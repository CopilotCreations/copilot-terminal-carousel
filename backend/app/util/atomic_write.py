"""Atomic file write utility to prevent partial writes."""
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def atomic_write_json(path: Path, data: Any) -> None:
    """Write JSON data to a file atomically.

    Uses a temporary file and rename to ensure the target file
    is never in a partially written state.

    Args:
        path: Target file path
        data: Data to serialize as JSON
    """
    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file in same directory for atomic rename
    fd, temp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=".tmp_",
        suffix=".json",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())

        # Atomic rename
        temp = Path(temp_path)
        temp.replace(path)
    except Exception:
        # Clean up temp file on error
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def read_json_file(path: Path) -> Any:
    """Read and parse a JSON file.

    Args:
        path: File path to read

    Returns:
        Parsed JSON data

    Raises:
        FileNotFoundError: If file does not exist
        json.JSONDecodeError: If file is not valid JSON
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
