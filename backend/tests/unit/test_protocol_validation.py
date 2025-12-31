"""Unit tests for WebSocket protocol message validation."""
import pytest
from pydantic import ValidationError

from app.ws.protocol import (
    ClientMessage,
    ErrorCodes,
    ErrorMessage,
    parse_client_message,
    ServerHelloMessage,
    SessionAttachMessage,
    SessionCreateMessage,
    SessionCreatedMessage,
    SessionInfo,
    SessionListMessage,
    SessionTerminateMessage,
    TerminalInputMessage,
    TerminalResizeMessage,
    utc_now_iso,
)


class TestClientMessageParsing:
    """Tests for parsing client messages."""

    def test_parse_session_create(self) -> None:
        """Test parsing session.create message."""
        data = {"type": "session.create"}
        message = parse_client_message(data)
        assert isinstance(message, SessionCreateMessage)
        assert message.type == "session.create"

    def test_parse_session_attach(self) -> None:
        """Test parsing session.attach message."""
        session_id = "12345678-1234-1234-1234-123456789abc"
        data = {"type": "session.attach", "sessionId": session_id}
        message = parse_client_message(data)
        assert isinstance(message, SessionAttachMessage)
        assert message.sessionId == session_id

    def test_parse_session_list(self) -> None:
        """Test parsing session.list message."""
        data = {"type": "session.list"}
        message = parse_client_message(data)
        assert isinstance(message, SessionListMessage)

    def test_parse_session_terminate(self) -> None:
        """Test parsing session.terminate message."""
        session_id = "12345678-1234-1234-1234-123456789abc"
        data = {"type": "session.terminate", "sessionId": session_id}
        message = parse_client_message(data)
        assert isinstance(message, SessionTerminateMessage)
        assert message.sessionId == session_id

    def test_parse_term_in(self) -> None:
        """Test parsing term.in message."""
        session_id = "12345678-1234-1234-1234-123456789abc"
        data = {"type": "term.in", "sessionId": session_id, "data": "hello\r\n"}
        message = parse_client_message(data)
        assert isinstance(message, TerminalInputMessage)
        assert message.data == "hello\r\n"

    def test_parse_term_resize(self) -> None:
        """Test parsing term.resize message."""
        session_id = "12345678-1234-1234-1234-123456789abc"
        data = {"type": "term.resize", "sessionId": session_id, "cols": 80, "rows": 24}
        message = parse_client_message(data)
        assert isinstance(message, TerminalResizeMessage)
        assert message.cols == 80
        assert message.rows == 24

    def test_parse_unknown_type_raises(self) -> None:
        """Test that unknown message type raises ValueError."""
        data = {"type": "unknown.message"}
        with pytest.raises(ValueError, match="Unknown message type"):
            parse_client_message(data)


class TestMessageValidation:
    """Tests for message validation rules."""

    def test_session_create_rejects_extra_fields(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError):
            SessionCreateMessage(type="session.create", extra_field="bad")  # type: ignore

    def test_session_attach_requires_session_id(self) -> None:
        """Test that sessionId is required."""
        with pytest.raises(ValidationError):
            SessionAttachMessage(type="session.attach")  # type: ignore

    def test_session_attach_validates_session_id_length(self) -> None:
        """Test that sessionId must be 36 characters."""
        with pytest.raises(ValidationError):
            SessionAttachMessage(type="session.attach", sessionId="short")

    def test_term_in_requires_data(self) -> None:
        """Test that term.in requires data field."""
        with pytest.raises(ValidationError):
            TerminalInputMessage(
                type="term.in",
                sessionId="12345678-1234-1234-1234-123456789abc",
            )  # type: ignore

    def test_term_resize_requires_positive_dimensions(self) -> None:
        """Test that resize requires positive dimensions."""
        with pytest.raises(ValidationError):
            TerminalResizeMessage(
                type="term.resize",
                sessionId="12345678-1234-1234-1234-123456789abc",
                cols=0,
                rows=24,
            )


class TestServerMessages:
    """Tests for server message creation."""

    def test_server_hello_message(self) -> None:
        """Test ServerHelloMessage creation."""
        msg = ServerHelloMessage(serverTime=utc_now_iso())
        assert msg.type == "server.hello"
        assert msg.protocolVersion == 1
        assert msg.serverTime.endswith("Z")

    def test_error_message(self) -> None:
        """Test ErrorMessage creation."""
        msg = ErrorMessage(
            code=ErrorCodes.SESSION_NOT_FOUND,
            message="Session not found",
        )
        assert msg.type == "error"
        assert msg.code == "SESSION_NOT_FOUND"

    def test_session_created_message(self) -> None:
        """Test SessionCreatedMessage creation."""
        session_info = SessionInfo(
            sessionId="12345678-1234-1234-1234-123456789abc",
            status="running",
            createdAt="2025-01-01T00:00:00.000Z",
            lastActivityAt="2025-01-01T00:00:00.000Z",
            workspacePath="C:\\test\\workspace",
            pid=12345,
            cols=120,
            rows=30,
        )
        msg = SessionCreatedMessage(session=session_info)
        assert msg.type == "session.created"
        assert msg.session.status == "running"


class TestUtcNowIso:
    """Tests for UTC timestamp generation."""

    def test_utc_now_iso_format(self) -> None:
        """Test that utc_now_iso returns correct format."""
        ts = utc_now_iso()
        assert ts.endswith("Z")
        # Should match pattern: YYYY-MM-DDTHH:MM:SS.sssZ
        assert len(ts) == 24
        assert ts[4] == "-"
        assert ts[7] == "-"
        assert ts[10] == "T"
        assert ts[13] == ":"
        assert ts[16] == ":"
        assert ts[19] == "."
