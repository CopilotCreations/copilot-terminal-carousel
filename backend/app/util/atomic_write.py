"""Atomic file write utility to prevent partial writes."""
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


def atomic_write_json(path: Path, data: Any, max_retries: int = 5) -> None:
    """Write JSON data to a file atomically.

    Uses a temporary file and rename to ensure the target file
    is never in a partially written state.

    Args:
        path: Target file path
        data: Data to serialize as JSON
        max_retries: Maximum retries for Windows file access issues
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

        # Atomic rename with retry for Windows file locking issues
        temp = Path(temp_path)
        last_error: Exception | None = None
        for attempt in range(max_retries):
            try:
                temp.replace(path)
                return
            except PermissionError as e:
                # On Windows, file may be locked by another process
                if sys.platform == "win32" and attempt < max_retries - 1:
                    last_error = e
                    time.sleep(0.1 * (attempt + 1))
                else:
                    raise
        if last_error:
            raise last_error
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
