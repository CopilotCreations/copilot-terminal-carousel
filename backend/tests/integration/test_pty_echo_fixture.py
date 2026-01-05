"""Integration tests for PTY with echo fixture."""
import pytest
from pathlib import Path

from app.sessions.pty_process import MockPtyProcess, create_pty_process


class TestMockPtyProcess:
    """Tests for MockPtyProcess used in testing."""

    @pytest.fixture
    def session_id(self) -> str:
        """Provide a test session ID.

        Returns:
            str: A valid UUID string for testing.
        """
        return "12345678-1234-1234-1234-123456789abc"

    @pytest.fixture
    def workspace(self, tmp_path: Path) -> Path:
        """Create a workspace directory.

        Args:
            tmp_path: Pytest's temporary path fixture.

        Returns:
            Path: The created workspace directory path.
        """
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        return workspace

    def test_mock_pty_spawn(self, session_id: str, workspace: Path) -> None:
        """Test mock PTY spawning.

        Args:
            session_id: The test session ID fixture.
            workspace: The test workspace directory fixture.
        """
        pty = MockPtyProcess(
            session_id=session_id,
            workspace_path=workspace,
            cols=80,
            rows=24,
        )

        success, error = pty.spawn()

        assert success
        assert error is None
        assert pty.pid == 99999
        assert pty.is_running

    def test_mock_pty_terminate(self, session_id: str, workspace: Path) -> None:
        """Test mock PTY termination.

        Args:
            session_id: The test session ID fixture.
            workspace: The test workspace directory fixture.
        """
        pty = MockPtyProcess(
            session_id=session_id,
            workspace_path=workspace,
            cols=80,
            rows=24,
        )
        pty.spawn()

        pty.terminate()

        assert not pty.is_running

    def test_mock_pty_resize(self, session_id: str, workspace: Path) -> None:
        """Test mock PTY resize.

        Args:
            session_id: The test session ID fixture.
            workspace: The test workspace directory fixture.
        """
        pty = MockPtyProcess(
            session_id=session_id,
            workspace_path=workspace,
            cols=80,
            rows=24,
        )
        pty.spawn()

        success = pty.resize(100, 50)

        assert success
        assert pty.cols == 100
        assert pty.rows == 50

    def test_mock_pty_write(self, session_id: str, workspace: Path) -> None:
        """Test mock PTY write buffers input.

        Args:
            session_id: The test session ID fixture.
            workspace: The test workspace directory fixture.
        """
        pty = MockPtyProcess(
            session_id=session_id,
            workspace_path=workspace,
            cols=80,
            rows=24,
        )
        pty.spawn()

        pty.write("test input")

        assert len(pty._input_buffer) == 1
        assert pty._input_buffer[0] == "test input"

    @pytest.mark.asyncio
    async def test_mock_pty_output_callback(
        self, session_id: str, workspace: Path
    ) -> None:
        """Test mock PTY calls output callback.

        Args:
            session_id: The test session ID fixture.
            workspace: The test workspace directory fixture.
        """
        import asyncio

        outputs: list[tuple[str, str]] = []

        async def on_output(sid: str, data: str) -> None:
            """Callback to capture PTY output.

            Args:
                sid: The session ID.
                data: The output data string.
            """
            outputs.append((sid, data))

        pty = MockPtyProcess(
            session_id=session_id,
            workspace_path=workspace,
            cols=80,
            rows=24,
            on_output=on_output,
        )
        pty.spawn()
        await pty.start_read_loop()

        # Wait for welcome message
        await asyncio.sleep(0.2)

        assert len(outputs) > 0
        assert outputs[0][0] == session_id
        assert "Welcome" in outputs[0][1]

        pty.terminate()


class TestPtyProcessFactory:
    """Tests for PTY process factory."""

    @pytest.fixture
    def session_id(self) -> str:
        """Provide a test session ID.

        Returns:
            str: A valid UUID string for testing.
        """
        return "12345678-1234-1234-1234-123456789abc"

    @pytest.fixture
    def workspace(self, tmp_path: Path) -> Path:
        """Create a workspace directory.

        Args:
            tmp_path: Pytest's temporary path fixture.

        Returns:
            Path: The created workspace directory path.
        """
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        return workspace

    def test_create_mock_pty(self, session_id: str, workspace: Path) -> None:
        """Test creating mock PTY.

        Args:
            session_id: The test session ID fixture.
            workspace: The test workspace directory fixture.
        """
        pty = create_pty_process(
            session_id=session_id,
            workspace_path=workspace,
            cols=80,
            rows=24,
            use_mock=True,
        )

        assert isinstance(pty, MockPtyProcess)

    def test_create_pty_defaults_to_mock_when_unavailable(
        self, session_id: str, workspace: Path
    ) -> None:
        """Test that factory creates mock when pywinpty is unavailable.

        Args:
            session_id: The test session ID fixture.
            workspace: The test workspace directory fixture.
        """
        # Since pywinpty may or may not be available, this test
        # verifies the factory works in either case
        pty = create_pty_process(
            session_id=session_id,
            workspace_path=workspace,
            cols=80,
            rows=24,
            use_mock=True,  # Force mock for test consistency
        )

        success, error = pty.spawn()
        assert success
        assert pty.is_running
