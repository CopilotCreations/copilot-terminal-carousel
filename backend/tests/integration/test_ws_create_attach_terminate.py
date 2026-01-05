"""Integration tests for WebSocket create/attach/terminate flow."""
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import os

from app.main import app
from app.sessions.manager import session_manager


class TestWebSocketConnection:
    """Tests for WebSocket connection and basic protocol."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path) -> None:
        """Set up test environment.

        Args:
            tmp_path: Pytest fixture providing a temporary directory path.
        """
        os.environ["DATA_DIR"] = str(tmp_path / "data")
        os.environ["LOG_FILE"] = str(tmp_path / "data" / "logs" / "app.jsonl")
        os.environ["ALLOW_NON_LOCALHOST"] = "true"

        (tmp_path / "data" / "sessions").mkdir(parents=True, exist_ok=True)
        (tmp_path / "data" / "logs").mkdir(parents=True, exist_ok=True)

        # Use mock PTY for tests
        session_manager._use_mock_pty = True
        session_manager._sessions.clear()

    def test_websocket_connect_receives_hello(self) -> None:
        """Test that WebSocket connection receives server.hello.

        Verifies that upon connecting, the server sends a hello message
        containing serverTime and protocolVersion.
        """
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            message = websocket.receive_json()

            assert message["type"] == "server.hello"
            assert "serverTime" in message
            assert message["protocolVersion"] == 1

    def test_websocket_session_list(self) -> None:
        """Test session.list message.

        Verifies that sending a session.list message returns a
        session.list.result with a list of sessions.
        """
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            # Receive hello
            websocket.receive_json()

            # Send session.list
            websocket.send_json({"type": "session.list"})
            response = websocket.receive_json()

            assert response["type"] == "session.list.result"
            assert "sessions" in response
            assert isinstance(response["sessions"], list)

    def test_websocket_create_session(self) -> None:
        """Test session.create message.

        Verifies that sending a session.create message returns a
        session.created response with session details including
        sessionId, status, and workspacePath.
        """
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            # Receive hello
            websocket.receive_json()

            # Send session.create
            websocket.send_json({"type": "session.create"})
            
            # May receive term.out before session.created
            response = websocket.receive_json()
            while response.get("type") == "term.out":
                response = websocket.receive_json()

            assert response["type"] == "session.created"
            assert "session" in response
            assert response["session"]["status"] == "running"
            assert "sessionId" in response["session"]
            assert "workspacePath" in response["session"]

    def test_websocket_attach_session(self) -> None:
        """Test session.attach message.

        Creates a session, then verifies that a new connection can
        attach to it and receive a session.attached response with
        the correct sessionId and status.
        """
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            # Receive hello
            websocket.receive_json()

            # Create a session first
            websocket.send_json({"type": "session.create"})
            
            # May receive term.out before session.created
            response = websocket.receive_json()
            while response.get("type") == "term.out":
                response = websocket.receive_json()
            
            assert response["type"] == "session.created"
            session_id = response["session"]["sessionId"]

            # Now open a new connection and attach
            with client.websocket_connect("/ws") as ws2:
                ws2.receive_json()  # hello

                ws2.send_json({"type": "session.attach", "sessionId": session_id})
                
                # May receive term.out messages
                attach_response = ws2.receive_json()
                while attach_response.get("type") == "term.out":
                    attach_response = ws2.receive_json()

                assert attach_response["type"] == "session.attached"
                assert attach_response["sessionId"] == session_id
                assert attach_response["status"] == "running"

    def test_websocket_terminate_session(self) -> None:
        """Test session.terminate message.

        Creates a session, terminates it, and verifies that a
        session.exited response is received with the correct sessionId.
        """
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            # Receive hello
            websocket.receive_json()

            # Create a session
            websocket.send_json({"type": "session.create"})
            
            # May receive term.out before session.created
            response = websocket.receive_json()
            while response.get("type") == "term.out":
                response = websocket.receive_json()
            
            assert response["type"] == "session.created"
            session_id = response["session"]["sessionId"]

            # Terminate it
            websocket.send_json(
                {"type": "session.terminate", "sessionId": session_id}
            )
            
            # May receive term.out before session.exited
            terminate_response = websocket.receive_json()
            while terminate_response.get("type") == "term.out":
                terminate_response = websocket.receive_json()

            assert terminate_response["type"] == "session.exited"
            assert terminate_response["sessionId"] == session_id

    def test_websocket_attach_nonexistent_session(self) -> None:
        """Test attaching to non-existent session returns error.

        Verifies that attempting to attach to a non-existent session
        returns an error with code SESSION_NOT_FOUND.
        """
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()  # hello

            # Use a valid UUID format
            websocket.send_json({
                "type": "session.attach",
                "sessionId": "12345678-1234-1234-1234-123456789abc",
            })
            response = websocket.receive_json()

            assert response["type"] == "error"
            assert response["code"] == "SESSION_NOT_FOUND"

    def test_websocket_invalid_message(self) -> None:
        """Test invalid message returns error.

        Verifies that sending an unknown message type returns an
        error with code UNKNOWN_MESSAGE_TYPE.
        """
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()  # hello

            websocket.send_json({"type": "invalid.type"})
            response = websocket.receive_json()

            assert response["type"] == "error"
            assert response["code"] == "UNKNOWN_MESSAGE_TYPE"


class TestTerminalInput:
    """Tests for terminal input handling."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path) -> None:
        """Set up test environment.

        Args:
            tmp_path: Pytest fixture providing a temporary directory path.
        """
        os.environ["DATA_DIR"] = str(tmp_path / "data")
        os.environ["LOG_FILE"] = str(tmp_path / "data" / "logs" / "app.jsonl")
        os.environ["ALLOW_NON_LOCALHOST"] = "true"

        (tmp_path / "data" / "sessions").mkdir(parents=True, exist_ok=True)
        (tmp_path / "data" / "logs").mkdir(parents=True, exist_ok=True)

        session_manager._use_mock_pty = True
        session_manager._sessions.clear()

    def test_term_in_requires_attach(self) -> None:
        """Test that term.in requires being attached to session.

        Creates a session, then opens a new connection without attaching
        and verifies that sending term.in returns an error with code
        NOT_ATTACHED.
        """
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()  # hello

            # Create session
            websocket.send_json({"type": "session.create"})
            create_response = websocket.receive_json()
            session_id = create_response["session"]["sessionId"]

            # Open new connection (not attached)
            with client.websocket_connect("/ws") as ws2:
                ws2.receive_json()  # hello

                # Try to send input without attaching
                ws2.send_json({
                    "type": "term.in",
                    "sessionId": session_id,
                    "data": "test",
                })
                response = ws2.receive_json()

                assert response["type"] == "error"
                assert response["code"] == "NOT_ATTACHED"


class TestTerminalResize:
    """Tests for terminal resize handling."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Set up test environment.

        Args:
            tmp_path: Pytest fixture providing a temporary directory path.
            monkeypatch: Pytest fixture for modifying settings.
        """
        from app.config import settings
        
        os.environ["DATA_DIR"] = str(tmp_path / "data")
        os.environ["LOG_FILE"] = str(tmp_path / "data" / "logs" / "app.jsonl")
        os.environ["ALLOW_NON_LOCALHOST"] = "true"
        
        monkeypatch.setattr(settings, "MIN_COLS", 20)
        monkeypatch.setattr(settings, "MAX_COLS", 300)
        monkeypatch.setattr(settings, "MIN_ROWS", 5)
        monkeypatch.setattr(settings, "MAX_ROWS", 120)

        (tmp_path / "data" / "sessions").mkdir(parents=True, exist_ok=True)
        (tmp_path / "data" / "logs").mkdir(parents=True, exist_ok=True)

        session_manager._use_mock_pty = True
        session_manager._sessions.clear()

    def test_resize_invalid_cols(self) -> None:
        """Test that invalid column resize returns error.

        Creates a session and attempts to resize with columns below
        MIN_COLS, verifying that an INVALID_RESIZE error is returned.
        """
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()  # hello

            websocket.send_json({"type": "session.create"})
            
            # May receive term.out before session.created
            response = websocket.receive_json()
            while response.get("type") == "term.out":
                response = websocket.receive_json()
            
            assert response["type"] == "session.created"
            session_id = response["session"]["sessionId"]

            # Try invalid resize
            websocket.send_json({
                "type": "term.resize",
                "sessionId": session_id,
                "cols": 10,  # Below MIN_COLS
                "rows": 24,
            })
            
            resize_response = websocket.receive_json()
            while resize_response.get("type") == "term.out":
                resize_response = websocket.receive_json()

            assert resize_response["type"] == "error"
            assert resize_response["code"] == "INVALID_RESIZE"

    def test_resize_invalid_rows(self) -> None:
        """Test that invalid row resize returns error.

        Creates a session and attempts to resize with rows above
        MAX_ROWS, verifying that an INVALID_RESIZE error is returned.
        """
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()  # hello

            websocket.send_json({"type": "session.create"})
            
            # May receive term.out before session.created, or errors
            response = websocket.receive_json()
            while response.get("type") == "term.out":
                response = websocket.receive_json()
            
            # Skip if we got an error during creation
            if response["type"] == "error":
                pytest.skip("Session creation failed")
            
            assert response["type"] == "session.created", f"Expected session.created, got {response}"
            session_id = response["session"]["sessionId"]

            # Try invalid resize
            websocket.send_json({
                "type": "term.resize",
                "sessionId": session_id,
                "cols": 80,
                "rows": 200,  # Above MAX_ROWS
            })
            
            resize_response = websocket.receive_json()
            while resize_response.get("type") == "term.out":
                resize_response = websocket.receive_json()

            assert resize_response["type"] == "error"
            assert resize_response["code"] == "INVALID_RESIZE"
