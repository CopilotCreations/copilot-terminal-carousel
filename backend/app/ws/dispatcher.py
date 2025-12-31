"""WebSocket message dispatcher for routing messages to handlers."""
import json
import logging
from typing import Any, Callable, Awaitable

from pydantic import ValidationError

from app.ws.protocol import (
    ClientMessage,
    ErrorCodes,
    ErrorMessage,
    parse_client_message,
    SessionCreateMessage,
    SessionAttachMessage,
    SessionListMessage,
    SessionTerminateMessage,
    TerminalInputMessage,
    TerminalResizeMessage,
)
from app.logging_setup import get_logger

logger = get_logger(__name__)


# Type alias for async handler functions
Handler = Callable[[str, ClientMessage], Awaitable[dict[str, Any] | None]]


class MessageDispatcher:
    """Routes WebSocket messages to appropriate handlers."""

    def __init__(self) -> None:
        """Initialize the dispatcher."""
        self._handlers: dict[str, Handler] = {}

    def register(self, message_type: str, handler: Handler) -> None:
        """Register a handler for a message type.

        Args:
            message_type: Message type string
            handler: Async handler function
        """
        self._handlers[message_type] = handler

    async def dispatch(
        self, client_id: str, raw_message: str
    ) -> dict[str, Any] | None:
        """Parse and dispatch a message to the appropriate handler.

        Args:
            client_id: Client identifier
            raw_message: Raw JSON message string

        Returns:
            Response dict or None if no response needed
        """
        # Parse JSON
        try:
            data = json.loads(raw_message)
        except json.JSONDecodeError as e:
            logger.warning(
                "Invalid JSON received",
                extra={"clientId": client_id, "error": str(e)},
            )
            return ErrorMessage(
                code=ErrorCodes.INVALID_MESSAGE,
                message=f"Invalid JSON: {str(e)}",
            ).model_dump()

        # Get message type
        msg_type = data.get("type")
        if not msg_type:
            logger.warning(
                "Message missing type field",
                extra={"clientId": client_id},
            )
            return ErrorMessage(
                code=ErrorCodes.INVALID_MESSAGE,
                message="Message must have a 'type' field",
            ).model_dump()

        # Parse and validate message
        try:
            message = parse_client_message(data)
        except ValueError as e:
            logger.warning(
                "Unknown message type",
                extra={"clientId": client_id, "type": msg_type},
            )
            return ErrorMessage(
                code=ErrorCodes.UNKNOWN_MESSAGE_TYPE,
                message=str(e),
            ).model_dump()
        except ValidationError as e:
            logger.warning(
                "Message validation failed",
                extra={"clientId": client_id, "type": msg_type, "errors": str(e)},
            )
            # Summarize validation errors
            error_summary = "; ".join(
                f"{err['loc']}: {err['msg']}" for err in e.errors()
            )
            return ErrorMessage(
                code=ErrorCodes.INVALID_MESSAGE,
                message=error_summary,
            ).model_dump()

        # Find handler
        handler = self._handlers.get(msg_type)
        if not handler:
            logger.warning(
                "No handler registered for message type",
                extra={"clientId": client_id, "type": msg_type},
            )
            return ErrorMessage(
                code=ErrorCodes.UNKNOWN_MESSAGE_TYPE,
                message=f"Unknown message type: {msg_type}",
            ).model_dump()

        # Dispatch to handler
        try:
            logger.debug(
                f"Dispatching message",
                extra={"clientId": client_id, "type": msg_type},
            )
            return await handler(client_id, message)
        except Exception as e:
            logger.error(
                f"Handler error: {e}",
                extra={"clientId": client_id, "type": msg_type},
                exc_info=True,
            )
            return ErrorMessage(
                code=ErrorCodes.INTERNAL_ERROR,
                message="Unhandled server error. See logs.",
            ).model_dump()


# Global dispatcher instance
dispatcher = MessageDispatcher()
