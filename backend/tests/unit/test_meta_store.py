"""Unit tests for meta store."""
import pytest
from pathlib import Path

from app.persistence.meta_store import MetaStore, SessionMeta


class TestMetaStore:
    """Tests for MetaStore functionality."""

    @pytest.fixture
    def meta_store(self, tmp_path: Path) -> MetaStore:
        """Create a MetaStore with a temp path."""
        return MetaStore(base_path=tmp_path / "sessions")

    @pytest.fixture
    def session_id(self) -> str:
        """Provide a test session ID."""
        return "12345678-1234-1234-1234-123456789abc"

    def test_create_meta(self, meta_store: MetaStore, session_id: str) -> None:
        """Test creating session metadata."""
        meta = meta_store.create(
            session_id=session_id,
            workspace_path="C:\\test\\workspace",
            copilot_path="copilot.exe",
            pid=12345,
            cols=120,
            rows=30,
        )

        assert meta.sessionId == session_id
        assert meta.status == "running"
        assert meta.pid == 12345
        assert meta.cols == 120
        assert meta.rows == 30
        assert meta.error is None

    def test_create_meta_with_error(
        self, meta_store: MetaStore, session_id: str
    ) -> None:
        """Test creating session metadata with spawn error."""
        meta = meta_store.create(
            session_id=session_id,
            workspace_path="C:\\test\\workspace",
            copilot_path="copilot.exe",
            pid=None,
            cols=120,
            rows=30,
            error={"code": "SPAWN_FAILED", "message": "Not found"},
        )

        assert meta.status == "exited"
        assert meta.pid is None
        assert meta.error is not None
        assert meta.error["code"] == "SPAWN_FAILED"

    def test_load_meta(self, meta_store: MetaStore, session_id: str) -> None:
        """Test loading session metadata."""
        meta_store.create(
            session_id=session_id,
            workspace_path="C:\\test\\workspace",
            copilot_path="copilot.exe",
            pid=12345,
            cols=120,
            rows=30,
        )

        loaded = meta_store.load(session_id)
        assert loaded is not None
        assert loaded.sessionId == session_id
        assert loaded.pid == 12345

    def test_load_meta_not_found(self, meta_store: MetaStore) -> None:
        """Test loading non-existent metadata returns None."""
        loaded = meta_store.load("nonexistent-id-1234567890123456")
        assert loaded is None

    def test_update_activity(self, meta_store: MetaStore, session_id: str) -> None:
        """Test updating last activity timestamp."""
        meta = meta_store.create(
            session_id=session_id,
            workspace_path="C:\\test\\workspace",
            copilot_path="copilot.exe",
            pid=12345,
            cols=120,
            rows=30,
        )
        original_activity = meta.lastActivityAt

        import time
        time.sleep(0.01)  # Ensure timestamp changes

        meta_store.update_activity(session_id)

        loaded = meta_store.load(session_id)
        assert loaded is not None
        assert loaded.lastActivityAt >= original_activity

    def test_update_status(self, meta_store: MetaStore, session_id: str) -> None:
        """Test updating session status."""
        meta_store.create(
            session_id=session_id,
            workspace_path="C:\\test\\workspace",
            copilot_path="copilot.exe",
            pid=12345,
            cols=120,
            rows=30,
        )

        meta_store.update_status(session_id, "exited", 0)

        loaded = meta_store.load(session_id)
        assert loaded is not None
        assert loaded.status == "exited"
        assert loaded.exitCode == 0

    def test_update_dimensions(self, meta_store: MetaStore, session_id: str) -> None:
        """Test updating terminal dimensions."""
        meta_store.create(
            session_id=session_id,
            workspace_path="C:\\test\\workspace",
            copilot_path="copilot.exe",
            pid=12345,
            cols=120,
            rows=30,
        )

        meta_store.update_dimensions(session_id, 80, 24)

        loaded = meta_store.load(session_id)
        assert loaded is not None
        assert loaded.cols == 80
        assert loaded.rows == 24
