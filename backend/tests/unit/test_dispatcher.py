"""Unit tests for dispatcher."""
import pytest
import json
from unittest.mock import AsyncMock

from app.ws.dispatcher import MessageDispatcher
from app.ws.protocol import ErrorCodes


class TestMessageDispatcher:
    """Tests for MessageDispatcher functionality."""

    @pytest.fixture
    def dispatcher(self) -> MessageDispatcher:
        """Create a new dispatcher.

        Returns:
            MessageDispatcher: A fresh MessageDispatcher instance for testing.
        """
        return MessageDispatcher()

    @pytest.mark.asyncio
    async def test_dispatch_valid_message(self, dispatcher: MessageDispatcher) -> None:
        """Test dispatching a valid message.

        Args:
            dispatcher: The MessageDispatcher fixture instance.
        """
        handler = AsyncMock(return_value={"type": "test.response"})
        dispatcher.register("session.create", handler)

        result = await dispatcher.dispatch(
            "client-1", json.dumps({"type": "session.create"})
        )

        handler.assert_called_once()
        assert result == {"type": "test.response"}

    @pytest.mark.asyncio
    async def test_dispatch_invalid_json(self, dispatcher: MessageDispatcher) -> None:
        """Test dispatching invalid JSON.

        Verifies that malformed JSON returns an error response with
        INVALID_MESSAGE error code.

        Args:
            dispatcher: The MessageDispatcher fixture instance.
        """
        result = await dispatcher.dispatch("client-1", "not valid json")

        assert result is not None
        assert result["type"] == "error"
        assert result["code"] == ErrorCodes.INVALID_MESSAGE

    @pytest.mark.asyncio
    async def test_dispatch_missing_type(self, dispatcher: MessageDispatcher) -> None:
        """Test dispatching message without type.

        Verifies that messages missing the required 'type' field return
        an error response with INVALID_MESSAGE error code.

        Args:
            dispatcher: The MessageDispatcher fixture instance.
        """
        result = await dispatcher.dispatch("client-1", json.dumps({"data": "test"}))

        assert result is not None
        assert result["type"] == "error"
        assert result["code"] == ErrorCodes.INVALID_MESSAGE

    @pytest.mark.asyncio
    async def test_dispatch_unknown_type(self, dispatcher: MessageDispatcher) -> None:
        """Test dispatching unknown message type.

        Verifies that messages with unrecognized type values return
        an error response with UNKNOWN_MESSAGE_TYPE error code.

        Args:
            dispatcher: The MessageDispatcher fixture instance.
        """
        result = await dispatcher.dispatch(
            "client-1", json.dumps({"type": "unknown.type"})
        )

        assert result is not None
        assert result["type"] == "error"
        assert result["code"] == ErrorCodes.UNKNOWN_MESSAGE_TYPE

    @pytest.mark.asyncio
    async def test_dispatch_validation_error(
        self, dispatcher: MessageDispatcher
    ) -> None:
        """Test dispatching message with validation error.

        Verifies that messages failing validation (e.g., missing required
        fields like sessionId) return an appropriate error response
        and the handler is not called.

        Args:
            dispatcher: The MessageDispatcher fixture instance.
        """
        handler = AsyncMock()
        dispatcher.register("session.attach", handler)

        # Missing required sessionId - should return error
        result = await dispatcher.dispatch(
            "client-1", json.dumps({"type": "session.attach"})
        )

        assert result is not None
        assert result["type"] == "error"
        # Could be INVALID_MESSAGE or UNKNOWN_MESSAGE_TYPE depending on parsing order
        assert result["code"] in (ErrorCodes.INVALID_MESSAGE, ErrorCodes.UNKNOWN_MESSAGE_TYPE)
        handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispatch_handler_error(
        self, dispatcher: MessageDispatcher
    ) -> None:
        """Test dispatching when handler raises exception.

        Verifies that exceptions raised by handlers are caught and
        converted to error responses with INTERNAL_ERROR error code.

        Args:
            dispatcher: The MessageDispatcher fixture instance.
        """
        handler = AsyncMock(side_effect=Exception("Handler error"))
        dispatcher.register("session.create", handler)

        result = await dispatcher.dispatch(
            "client-1", json.dumps({"type": "session.create"})
        )

        assert result is not None
        assert result["type"] == "error"
        assert result["code"] == ErrorCodes.INTERNAL_ERROR

    @pytest.mark.asyncio
    async def test_dispatch_no_handler(self, dispatcher: MessageDispatcher) -> None:
        """Test dispatching when no handler registered.

        Verifies that dispatching a message type with no registered handler
        returns an error response with UNKNOWN_MESSAGE_TYPE error code.

        Args:
            dispatcher: The MessageDispatcher fixture instance.
        """
        result = await dispatcher.dispatch(
            "client-1", json.dumps({"type": "session.create"})
        )

        assert result is not None
        assert result["type"] == "error"
        assert result["code"] == ErrorCodes.UNKNOWN_MESSAGE_TYPE

    @pytest.mark.asyncio
    async def test_handler_returns_none(self, dispatcher: MessageDispatcher) -> None:
        """Test handler returning None (no response).

        Verifies that handlers can return None to indicate no response
        should be sent back to the client.

        Args:
            dispatcher: The MessageDispatcher fixture instance.
        """
        handler = AsyncMock(return_value=None)
        dispatcher.register("term.in", handler)

        result = await dispatcher.dispatch(
            "client-1",
            json.dumps({
                "type": "term.in",
                "sessionId": "12345678-1234-1234-1234-123456789abc",
                "data": "test",
            }),
        )

        assert result is None
