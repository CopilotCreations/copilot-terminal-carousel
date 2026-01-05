"""Unit tests for session manager."""
import pytest
from pathlib import Path
import os

from app.sessions.manager import SessionManager
from app.ws.protocol import ErrorCodes


class TestSessionManager:
    """Tests for SessionManager functionality."""

    @pytest.fixture
    def manager(self, tmp_path: Path) -> SessionManager:
        """Create a SessionManager with mock PTY.

        Args:
            tmp_path: Pytest fixture providing a temporary directory path.

        Returns:
            A SessionManager instance configured with mock PTY for testing.
        """
        # Set environment variable for DATA_DIR
        os.environ["DATA_DIR"] = str(tmp_path / "data")
        
        # Create directories
        (tmp_path / "data" / "sessions").mkdir(parents=True, exist_ok=True)

        return SessionManager(use_mock_pty=True)

    @pytest.mark.asyncio
    async def test_create_session_success(self, manager: SessionManager) -> None:
        """Test successful session creation.

        Args:
            manager: SessionManager fixture with mock PTY.
        """
        session, error_code, error_msg = await manager.create_session()

        assert session is not None
        assert error_code is None
        assert error_msg is None
        assert session.is_running
        assert session.pty.pid is not None

    @pytest.mark.asyncio
    async def test_create_session_max_sessions(
        self, manager: SessionManager, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that max sessions limit is enforced.

        Args:
            manager: SessionManager fixture with mock PTY.
            monkeypatch: Pytest fixture for patching attributes.
        """
        from app.config import settings

        original_max = settings.MAX_SESSIONS
        # Create 2 sessions when max is 2
        object.__setattr__(settings, "_MAX_SESSIONS_override", 2)
        monkeypatch.setattr(settings, "MAX_SESSIONS", 2)

        # Create 2 sessions
        await manager.create_session()
        await manager.create_session()

        # Third should fail
        session, error_code, error_msg = await manager.create_session()

        assert session is None
        assert error_code == ErrorCodes.MAX_SESSIONS_REACHED
        assert "Maximum running sessions" in (error_msg or "")

    @pytest.mark.asyncio
    async def test_get_session(self, manager: SessionManager) -> None:
        """Test getting a session by ID.

        Args:
            manager: SessionManager fixture with mock PTY.
        """
        created, _, _ = await manager.create_session()
        assert created is not None

        session = manager.get_session(created.session_id)
        assert session is not None
        assert session.session_id == created.session_id

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, manager: SessionManager) -> None:
        """Test getting a non-existent session returns None.

        Args:
            manager: SessionManager fixture with mock PTY.
        """
        session = manager.get_session("nonexistent-id-1234567890123456")
        assert session is None

    @pytest.mark.asyncio
    async def test_attach_session(self, manager: SessionManager) -> None:
        """Test attaching to a session.

        Args:
            manager: SessionManager fixture with mock PTY.
        """
        created, _, _ = await manager.create_session()
        assert created is not None

        session, error_code, error_msg = await manager.attach_session(
            created.session_id, "client-1"
        )

        assert session is not None
        assert error_code is None
        assert "client-1" in session.attached_clients

    @pytest.mark.asyncio
    async def test_attach_session_not_found(self, manager: SessionManager) -> None:
        """Test attaching to a non-existent session.

        Args:
            manager: SessionManager fixture with mock PTY.
        """
        session, error_code, error_msg = await manager.attach_session(
            "nonexistent-id-1234567890123456", "client-1"
        )

        assert session is None
        assert error_code == ErrorCodes.SESSION_NOT_FOUND

    @pytest.mark.asyncio
    async def test_terminate_session(self, manager: SessionManager) -> None:
        """Test terminating a session.

        Args:
            manager: SessionManager fixture with mock PTY.
        """
        created, _, _ = await manager.create_session()
        assert created is not None

        exit_code, error_code, error_msg = await manager.terminate_session(
            created.session_id
        )

        assert error_code is None
        assert not created.is_running

    @pytest.mark.asyncio
    async def test_terminate_session_not_found(self, manager: SessionManager) -> None:
        """Test terminating a non-existent session.

        Args:
            manager: SessionManager fixture with mock PTY.
        """
        exit_code, error_code, error_msg = await manager.terminate_session(
            "nonexistent-id-1234567890123456"
        )

        assert error_code == ErrorCodes.SESSION_NOT_FOUND

    @pytest.mark.asyncio
    async def test_send_input_success(self, manager: SessionManager) -> None:
        """Test sending input to a session.

        Args:
            manager: SessionManager fixture with mock PTY.
        """
        created, _, _ = await manager.create_session()
        assert created is not None

        success, error_code, error_msg = manager.send_input(
            created.session_id, "test input"
        )

        assert success
        assert error_code is None

    @pytest.mark.asyncio
    async def test_send_input_too_large(
        self, manager: SessionManager, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that large input is rejected.

        Args:
            manager: SessionManager fixture with mock PTY.
            monkeypatch: Pytest fixture for patching attributes.
        """
        from app.config import settings

        monkeypatch.setattr(settings, "MAX_INPUT_CHARS_PER_MESSAGE", 100)

        created, _, _ = await manager.create_session()
        assert created is not None

        large_input = "x" * 200
        success, error_code, error_msg = manager.send_input(
            created.session_id, large_input
        )

        assert not success
        assert error_code == ErrorCodes.INPUT_TOO_LARGE

    def test_send_input_session_not_found(self, manager: SessionManager) -> None:
        """Test sending input to non-existent session.

        Args:
            manager: SessionManager fixture with mock PTY.
        """
        success, error_code, error_msg = manager.send_input(
            "nonexistent-id-1234567890123456", "test"
        )

        assert not success
        assert error_code == ErrorCodes.SESSION_NOT_FOUND


class TestResizeSession:
    """Tests for session resize functionality."""

    @pytest.fixture
    def manager(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SessionManager:
        """Create a SessionManager with mock PTY and configured resize bounds.

        Args:
            tmp_path: Pytest fixture providing a temporary directory path.
            monkeypatch: Pytest fixture for patching attributes.

        Returns:
            A SessionManager instance configured with mock PTY and resize bounds.
        """
        from app.config import settings

        os.environ["DATA_DIR"] = str(tmp_path / "data")
        monkeypatch.setattr(settings, "MIN_COLS", 20)
        monkeypatch.setattr(settings, "MAX_COLS", 300)
        monkeypatch.setattr(settings, "MIN_ROWS", 5)
        monkeypatch.setattr(settings, "MAX_ROWS", 120)

        (tmp_path / "data" / "sessions").mkdir(parents=True, exist_ok=True)

        return SessionManager(use_mock_pty=True)

    @pytest.mark.asyncio
    async def test_resize_valid(self, manager: SessionManager) -> None:
        """Test valid resize.

        Args:
            manager: SessionManager fixture with mock PTY.
        """
        created, _, _ = await manager.create_session()
        assert created is not None

        success, error_code, error_msg = manager.resize_session(
            created.session_id, 80, 24
        )

        assert success
        assert error_code is None

    @pytest.mark.asyncio
    async def test_resize_cols_below_min(self, manager: SessionManager) -> None:
        """Test resize with columns below minimum.

        Args:
            manager: SessionManager fixture with mock PTY.
        """
        created, _, _ = await manager.create_session()
        assert created is not None

        success, error_code, error_msg = manager.resize_session(
            created.session_id, 10, 24
        )

        assert not success
        assert error_code == ErrorCodes.INVALID_RESIZE

    @pytest.mark.asyncio
    async def test_resize_cols_above_max(self, manager: SessionManager) -> None:
        """Test resize with columns above maximum.

        Args:
            manager: SessionManager fixture with mock PTY.
        """
        created, _, _ = await manager.create_session()
        assert created is not None

        success, error_code, error_msg = manager.resize_session(
            created.session_id, 400, 24
        )

        assert not success
        assert error_code == ErrorCodes.INVALID_RESIZE

    @pytest.mark.asyncio
    async def test_resize_rows_below_min(self, manager: SessionManager) -> None:
        """Test resize with rows below minimum.

        Args:
            manager: SessionManager fixture with mock PTY.
        """
        created, _, _ = await manager.create_session()
        assert created is not None

        success, error_code, error_msg = manager.resize_session(
            created.session_id, 80, 2
        )

        assert not success
        assert error_code == ErrorCodes.INVALID_RESIZE

    @pytest.mark.asyncio
    async def test_resize_rows_above_max(self, manager: SessionManager) -> None:
        """Test resize with rows above maximum.

        Args:
            manager: SessionManager fixture with mock PTY.
        """
        created, _, _ = await manager.create_session()
        assert created is not None

        success, error_code, error_msg = manager.resize_session(
            created.session_id, 80, 200
        )

        assert not success
        assert error_code == ErrorCodes.INVALID_RESIZE

    def test_resize_session_not_found(self, manager: SessionManager) -> None:
        """Test resize on non-existent session.

        Args:
            manager: SessionManager fixture with mock PTY.
        """
        success, error_code, error_msg = manager.resize_session(
            "nonexistent-id-1234567890123456", 80, 24
        )

        assert not success
        assert error_code == ErrorCodes.SESSION_NOT_FOUND
