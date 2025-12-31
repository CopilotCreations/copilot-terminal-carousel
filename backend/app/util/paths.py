"""Path utility functions for safe path handling."""
from pathlib import Path

from app.config import settings


def get_session_dir(session_id: str) -> Path:
    """Get the directory path for a session.

    Args:
        session_id: The session UUID

    Returns:
        Path to the session directory
    """
    return settings.sessions_dir / session_id


def get_workspace_path(session_id: str) -> Path:
    """Get the workspace directory path for a session.

    Args:
        session_id: The session UUID

    Returns:
        Path to the workspace directory
    """
    return get_session_dir(session_id) / "workspace"


def get_meta_path(session_id: str) -> Path:
    """Get the meta.json path for a session.

    Args:
        session_id: The session UUID

    Returns:
        Path to the meta.json file
    """
    return get_session_dir(session_id) / "meta.json"


def get_transcript_path(session_id: str) -> Path:
    """Get the transcript.jsonl path for a session.

    Args:
        session_id: The session UUID

    Returns:
        Path to the transcript.jsonl file
    """
    return get_session_dir(session_id) / "transcript.jsonl"


def get_index_path() -> Path:
    """Get the index.json path.

    Returns:
        Path to the index.json file
    """
    return settings.sessions_dir / "index.json"


def is_valid_workspace_path(path: Path, session_id: str) -> bool:
    """Check if a path is a valid workspace path for the given session.

    The workspace path must be under DATA_DIR/sessions/{session_id}/workspace.

    Args:
        path: The path to validate
        session_id: The session UUID

    Returns:
        True if the path is valid, False otherwise
    """
    expected_base = get_workspace_path(session_id).resolve()
    try:
        resolved = path.resolve()
        return resolved == expected_base or expected_base in resolved.parents
    except (OSError, ValueError):
        return False


def ensure_session_directories(session_id: str) -> Path:
    """Create all required directories for a session.

    Args:
        session_id: The session UUID

    Returns:
        Path to the workspace directory
    """
    session_dir = get_session_dir(session_id)
    workspace_dir = get_workspace_path(session_id)

    session_dir.mkdir(parents=True, exist_ok=True)
    workspace_dir.mkdir(parents=True, exist_ok=True)

    return workspace_dir
