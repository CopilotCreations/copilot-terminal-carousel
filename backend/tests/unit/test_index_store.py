"""Unit tests for index store."""
import json
import pytest
from pathlib import Path

from app.persistence.index_store import IndexStore


class TestIndexStore:
    """Tests for IndexStore functionality."""

    @pytest.fixture
    def index_store(self, tmp_path: Path) -> IndexStore:
        """Create an IndexStore with a temp path.

        Args:
            tmp_path: Pytest fixture providing a temporary directory path.

        Returns:
            An IndexStore instance configured to use a temporary index file.
        """
        index_path = tmp_path / "sessions" / "index.json"
        index_path.parent.mkdir(parents=True, exist_ok=True)
        return IndexStore(index_path=index_path)

    def test_load_empty_index(self, index_store: IndexStore) -> None:
        """Test loading when index doesn't exist returns empty structure.

        Args:
            index_store: The IndexStore fixture instance.
        """
        index = index_store.load()
        assert index["protocolVersion"] == 1
        assert index["sessions"] == []
        assert "updatedAt" in index

    def test_save_and_load(self, index_store: IndexStore) -> None:
        """Test saving and loading index.

        Args:
            index_store: The IndexStore fixture instance.
        """
        index = index_store.load()
        index["sessions"].append({
            "sessionId": "test-session-id-1234-567890123456",
            "status": "running",
            "createdAt": "2025-01-01T00:00:00.000Z",
            "lastActivityAt": "2025-01-01T00:00:00.000Z",
        })
        index_store.save(index)

        loaded = index_store.load()
        assert len(loaded["sessions"]) == 1
        assert loaded["sessions"][0]["sessionId"] == "test-session-id-1234-567890123456"

    def test_add_session(self, index_store: IndexStore) -> None:
        """Test adding a session to the index.

        Args:
            index_store: The IndexStore fixture instance.
        """
        session_id = "12345678-1234-1234-1234-123456789abc"
        index_store.add_session(
            session_id=session_id,
            status="running",
            created_at="2025-01-01T00:00:00.000Z",
            last_activity_at="2025-01-01T00:00:00.000Z",
        )

        index = index_store.load()
        assert len(index["sessions"]) == 1
        assert index["sessions"][0]["sessionId"] == session_id
        assert index["sessions"][0]["status"] == "running"

    def test_update_session_status(self, index_store: IndexStore) -> None:
        """Test updating a session's status.

        Args:
            index_store: The IndexStore fixture instance.
        """
        session_id = "12345678-1234-1234-1234-123456789abc"
        index_store.add_session(
            session_id=session_id,
            status="running",
            created_at="2025-01-01T00:00:00.000Z",
            last_activity_at="2025-01-01T00:00:00.000Z",
        )

        index_store.update_session_status(session_id, "exited")

        index = index_store.load()
        assert index["sessions"][0]["status"] == "exited"

    def test_get_all_sessions_sorted(self, index_store: IndexStore) -> None:
        """Test that sessions are returned sorted by createdAt descending.

        Args:
            index_store: The IndexStore fixture instance.
        """
        index_store.add_session(
            session_id="session-1-aaaaaaaaaaaaaaaaaaaaaaaa",
            status="running",
            created_at="2025-01-01T00:00:00.000Z",
            last_activity_at="2025-01-01T00:00:00.000Z",
        )
        index_store.add_session(
            session_id="session-2-bbbbbbbbbbbbbbbbbbbbbbbb",
            status="running",
            created_at="2025-01-02T00:00:00.000Z",
            last_activity_at="2025-01-02T00:00:00.000Z",
        )
        index_store.add_session(
            session_id="session-3-cccccccccccccccccccccccc",
            status="running",
            created_at="2025-01-01T12:00:00.000Z",
            last_activity_at="2025-01-01T12:00:00.000Z",
        )

        sessions = index_store.get_all_sessions()
        assert len(sessions) == 3
        # Should be sorted descending by createdAt
        assert sessions[0].sessionId == "session-2-bbbbbbbbbbbbbbbbbbbbbbbb"
        assert sessions[1].sessionId == "session-3-cccccccccccccccccccccccc"
        assert sessions[2].sessionId == "session-1-aaaaaaaaaaaaaaaaaaaaaaaa"

    def test_get_session(self, index_store: IndexStore) -> None:
        """Test getting a specific session.

        Args:
            index_store: The IndexStore fixture instance.
        """
        session_id = "12345678-1234-1234-1234-123456789abc"
        index_store.add_session(
            session_id=session_id,
            status="running",
            created_at="2025-01-01T00:00:00.000Z",
            last_activity_at="2025-01-01T00:00:00.000Z",
        )

        session = index_store.get_session(session_id)
        assert session is not None
        assert session.sessionId == session_id

    def test_get_session_not_found(self, index_store: IndexStore) -> None:
        """Test getting a non-existent session returns None.

        Args:
            index_store: The IndexStore fixture instance.
        """
        session = index_store.get_session("nonexistent-id-12345678901234")
        assert session is None

    def test_remove_session(self, index_store: IndexStore) -> None:
        """Test removing a session from the index.

        Args:
            index_store: The IndexStore fixture instance.
        """
        session_id = "12345678-1234-1234-1234-123456789abc"
        index_store.add_session(
            session_id=session_id,
            status="running",
            created_at="2025-01-01T00:00:00.000Z",
            last_activity_at="2025-01-01T00:00:00.000Z",
        )

        index_store.remove_session(session_id)

        sessions = index_store.get_all_sessions()
        assert len(sessions) == 0

    def test_atomic_write_produces_valid_json(self, index_store: IndexStore) -> None:
        """Test that atomic write produces valid JSON.

        Args:
            index_store: The IndexStore fixture instance.
        """
        session_id = "12345678-1234-1234-1234-123456789abc"
        index_store.add_session(
            session_id=session_id,
            status="running",
            created_at="2025-01-01T00:00:00.000Z",
            last_activity_at="2025-01-01T00:00:00.000Z",
        )

        # Verify the file contains valid JSON
        with open(index_store.index_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "protocolVersion" in data
        assert "updatedAt" in data
        assert "sessions" in data
        assert len(data["sessions"]) == 1

    def test_protocol_version(self, index_store: IndexStore) -> None:
        """Test that protocol version is set correctly.

        Args:
            index_store: The IndexStore fixture instance.
        """
        index = index_store.load()
        assert index["protocolVersion"] == IndexStore.PROTOCOL_VERSION
        assert index["protocolVersion"] == 1
