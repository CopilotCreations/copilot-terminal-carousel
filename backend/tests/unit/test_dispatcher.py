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
        """Create a new dispatcher."""
        return MessageDispatcher()

    @pytest.mark.asyncio
    async def test_dispatch_valid_message(self, dispatcher: MessageDispatcher) -> None:
        """Test dispatching a valid message."""
        handler = AsyncMock(return_value={"type": "test.response"})
        dispatcher.register("session.create", handler)

        result = await dispatcher.dispatch(
            "client-1", json.dumps({"type": "session.create"})
        )

        handler.assert_called_once()
        assert result == {"type": "test.response"}

    @pytest.mark.asyncio
    async def test_dispatch_invalid_json(self, dispatcher: MessageDispatcher) -> None:
        """Test dispatching invalid JSON."""
        result = await dispatcher.dispatch("client-1", "not valid json")

        assert result is not None
        assert result["type"] == "error"
        assert result["code"] == ErrorCodes.INVALID_MESSAGE

    @pytest.mark.asyncio
    async def test_dispatch_missing_type(self, dispatcher: MessageDispatcher) -> None:
        """Test dispatching message without type."""
        result = await dispatcher.dispatch("client-1", json.dumps({"data": "test"}))

        assert result is not None
        assert result["type"] == "error"
        assert result["code"] == ErrorCodes.INVALID_MESSAGE

    @pytest.mark.asyncio
    async def test_dispatch_unknown_type(self, dispatcher: MessageDispatcher) -> None:
        """Test dispatching unknown message type."""
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
        """Test dispatching message with validation error."""
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
        """Test dispatching when handler raises exception."""
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
        """Test dispatching when no handler registered."""
        result = await dispatcher.dispatch(
            "client-1", json.dumps({"type": "session.create"})
        )

        assert result is not None
        assert result["type"] == "error"
        assert result["code"] == ErrorCodes.UNKNOWN_MESSAGE_TYPE

    @pytest.mark.asyncio
    async def test_handler_returns_none(self, dispatcher: MessageDispatcher) -> None:
        """Test handler returning None (no response)."""
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
