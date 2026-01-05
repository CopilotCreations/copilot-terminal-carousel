"""Unit tests for path utilities."""
import pytest
from pathlib import Path
import os

from app.util.paths import (
    get_session_dir,
    get_workspace_path,
    get_meta_path,
    get_transcript_path,
    get_index_path,
    is_valid_workspace_path,
    ensure_session_directories,
)
from app.config import settings


class TestPathUtilities:
    """Tests for path utility functions."""

    @pytest.fixture
    def session_id(self) -> str:
        """Provide a test session ID.

        Returns:
            str: A valid UUID-formatted session ID for testing.
        """
        return "12345678-1234-1234-1234-123456789abc"

    def test_get_session_dir(self, session_id: str) -> None:
        """Test getting session directory path.

        Args:
            session_id: The session ID fixture.

        Verifies:
            The returned path contains the session ID and ends with it.
        """
        path = get_session_dir(session_id)
        assert session_id in str(path)
        assert str(path).endswith(session_id)

    def test_get_workspace_path(self, session_id: str) -> None:
        """Test getting workspace directory path.

        Args:
            session_id: The session ID fixture.

        Verifies:
            The returned path contains the session ID and ends with 'workspace'.
        """
        path = get_workspace_path(session_id)
        assert session_id in str(path)
        assert str(path).endswith("workspace")

    def test_get_meta_path(self, session_id: str) -> None:
        """Test getting meta.json path.

        Args:
            session_id: The session ID fixture.

        Verifies:
            The returned path contains the session ID and ends with 'meta.json'.
        """
        path = get_meta_path(session_id)
        assert session_id in str(path)
        assert str(path).endswith("meta.json")

    def test_get_transcript_path(self, session_id: str) -> None:
        """Test getting transcript.jsonl path.

        Args:
            session_id: The session ID fixture.

        Verifies:
            The returned path contains the session ID and ends with 'transcript.jsonl'.
        """
        path = get_transcript_path(session_id)
        assert session_id in str(path)
        assert str(path).endswith("transcript.jsonl")

    def test_get_index_path(self) -> None:
        """Test getting index.json path.

        Verifies:
            The returned path ends with 'index.json'.
        """
        path = get_index_path()
        assert str(path).endswith("index.json")

    def test_workspace_path_under_session_dir(self, session_id: str) -> None:
        """Test that workspace path is under session directory.

        Args:
            session_id: The session ID fixture.

        Verifies:
            The workspace path is a subdirectory of the session directory.
        """
        session_dir = get_session_dir(session_id)
        workspace = get_workspace_path(session_id)
        assert session_dir in workspace.parents


class TestWorkspacePathValidation:
    """Tests for workspace path validation."""

    @pytest.fixture
    def session_id(self) -> str:
        """Provide a test session ID.

        Returns:
            str: A valid UUID-formatted session ID for testing.
        """
        return "12345678-1234-1234-1234-123456789abc"

    def test_path_traversal_rejected(self, session_id: str) -> None:
        """Test that path traversal attempts are rejected.

        Args:
            session_id: The session ID fixture.

        Verifies:
            Paths containing '..' directory traversal are rejected as invalid.
        """
        # Try to escape with ..
        malicious_path = Path(f"data/sessions/{session_id}/workspace/../../../etc/passwd")
        assert not is_valid_workspace_path(malicious_path, session_id)

    def test_different_session_rejected(self, session_id: str) -> None:
        """Test that paths from different sessions are rejected.

        Args:
            session_id: The session ID fixture.

        Verifies:
            Workspace paths belonging to a different session are rejected.
        """
        other_session = "other-session-id-1234567890123456"
        path = get_workspace_path(other_session)
        assert not is_valid_workspace_path(path, session_id)
