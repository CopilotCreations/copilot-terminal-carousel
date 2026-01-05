"""WebSocket router and connection handling."""
import asyncio
import json
import time
import uuid
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.config import settings
from app.logging_setup import get_logger
from app.persistence.index_store import index_store
from app.sessions.manager import session_manager
from app.util.time import utc_now_iso
from app.ws.dispatcher import dispatcher
from app.ws.protocol import (
    ClientMessage,
    ErrorCodes,
    ErrorMessage,
    ServerHelloMessage,
    SessionAttachedMessage,
    SessionCreateMessage,
    SessionAttachMessage,
    SessionCreatedMessage,
    SessionExitedMessage,
    SessionListMessage,
    SessionListResultMessage,
    SessionRenameMessage,
    SessionRenamedMessage,
    SessionTerminateMessage,
    TerminalInputMessage,
    TerminalOutputMessage,
    TerminalResizeMessage,
)

logger = get_logger(__name__)

router = APIRouter()


class RateLimiter:
    """Simple rate limiter for WebSocket messages."""

    def __init__(self, max_messages: int = 200, window_seconds: float = 1.0) -> None:
        """Initialize rate limiter.

        Args:
            max_messages: Maximum messages per window
            window_seconds: Time window in seconds
        """
        self.max_messages = max_messages
        self.window_seconds = window_seconds
        self._message_times: dict[str, list[float]] = defaultdict(list)

    def check(self, client_id: str) -> bool:
        """Check if client is within rate limit.

        Args:
            client_id: Client identifier

        Returns:
            True if within limit, False if exceeded
        """
        now = time.time()
        window_start = now - self.window_seconds

        # Remove old timestamps
        self._message_times[client_id] = [
            t for t in self._message_times[client_id] if t > window_start
        ]

        # Check limit
        if len(self._message_times[client_id]) >= self.max_messages:
            return False

        # Record this message
        self._message_times[client_id].append(now)
        return True

    def cleanup(self, client_id: str) -> None:
        """Clean up rate limiter state for a client.

        Args:
            client_id: Client identifier
        """
        self._message_times.pop(client_id, None)


# Global rate limiter
rate_limiter = RateLimiter()


class WebSocketConnection:
    """Manages a single WebSocket connection."""

    def __init__(self, websocket: WebSocket, client_id: str) -> None:
        """Initialize connection.

        Args:
            websocket: FastAPI WebSocket
            client_id: Unique client identifier
        """
        self.websocket = websocket
        self.client_id = client_id
        self._attached_session: str | None = None

    async def send_json(self, data: dict[str, Any]) -> None:
        """Send JSON message to client.

        Args:
            data: Message data to send
        """
        if self.websocket.client_state == WebSocketState.CONNECTED:
            await self.websocket.send_json(data)

    async def handle_output(self, session_id: str, data: str) -> None:
        """Handle terminal output for this connection.

        Args:
            session_id: Session UUID
            data: Output data
        """
        if session_id == self._attached_session:
            await self.send_json(
                TerminalOutputMessage(sessionId=session_id, data=data).model_dump()
            )

    async def handle_exit(self, session_id: str, exit_code: int | None) -> None:
        """Handle session exit for this connection.

        Args:
            session_id: Session UUID
            exit_code: Exit code or None
        """
        if session_id == self._attached_session:
            await self.send_json(
                SessionExitedMessage(sessionId=session_id, exitCode=exit_code).model_dump()
            )

    def attach_to_session(self, session_id: str) -> None:
        """Attach this connection to a session.

        Args:
            session_id: Session UUID
        """
        self._attached_session = session_id

    def detach_from_session(self) -> None:
        """Detach from current session."""
        self._attached_session = None

    @property
    def attached_session(self) -> str | None:
        """Get currently attached session ID."""
        return self._attached_session


# Store active connections
_connections: dict[str, WebSocketConnection] = {}


def get_connection(client_id: str) -> WebSocketConnection | None:
    """Get a connection by client ID.

    Args:
        client_id: Unique client identifier.

    Returns:
        The WebSocketConnection if found, None otherwise.
    """
    return _connections.get(client_id)


# ============================================================================
# Message Handlers
# ============================================================================


async def handle_session_create(
    client_id: str, message: ClientMessage
) -> dict[str, Any] | None:
    """Handle session.create message.

    Creates a new terminal session and attaches the client to it.

    Args:
        client_id: Unique client identifier.
        message: The client message (SessionCreateMessage).

    Returns:
        SessionCreatedMessage on success, ErrorMessage on failure.
    """
    session, error_code, error_msg = await session_manager.create_session()

    if error_code:
        return ErrorMessage(code=error_code, message=error_msg or "").model_dump()

    if session:
        # Attach connection to session
        conn = get_connection(client_id)
        if conn:
            conn.attach_to_session(session.session_id)

        await session_manager.attach_session(session.session_id, client_id)

        return SessionCreatedMessage(session=session.to_session_info()).model_dump()

    return ErrorMessage(
        code=ErrorCodes.INTERNAL_ERROR,
        message="Failed to create session",
    ).model_dump()


async def handle_session_attach(
    client_id: str, message: ClientMessage
) -> dict[str, Any] | None:
    """Handle session.attach message.

    Attaches the client to an existing terminal session.

    Args:
        client_id: Unique client identifier.
        message: The client message (SessionAttachMessage).

    Returns:
        SessionAttachedMessage on success, ErrorMessage on failure.
    """
    assert isinstance(message, SessionAttachMessage)

    session, error_code, error_msg = await session_manager.attach_session(
        message.sessionId, client_id
    )

    if error_code:
        return ErrorMessage(code=error_code, message=error_msg or "").model_dump()

    if session:
        # Attach connection to session
        conn = get_connection(client_id)
        if conn:
            conn.attach_to_session(session.session_id)

        return SessionAttachedMessage(
            sessionId=session.session_id,
            status="running" if session.is_running else "exited",
        ).model_dump()

    return ErrorMessage(
        code=ErrorCodes.INTERNAL_ERROR,
        message="Failed to attach to session",
    ).model_dump()


async def handle_session_list(
    client_id: str, message: ClientMessage
) -> dict[str, Any] | None:
    """Handle session.list message.

    Returns a list of all available terminal sessions.

    Args:
        client_id: Unique client identifier.
        message: The client message (SessionListMessage).

    Returns:
        SessionListResultMessage containing the list of sessions.
    """
    sessions = session_manager.list_sessions()
    return SessionListResultMessage(sessions=sessions).model_dump()


async def handle_session_terminate(
    client_id: str, message: ClientMessage
) -> dict[str, Any] | None:
    """Handle session.terminate message.

    Terminates the specified terminal session.

    Args:
        client_id: Unique client identifier.
        message: The client message (SessionTerminateMessage).

    Returns:
        SessionExitedMessage on success, ErrorMessage on failure.
    """
    assert isinstance(message, SessionTerminateMessage)

    exit_code, error_code, error_msg = await session_manager.terminate_session(
        message.sessionId
    )

    if error_code:
        return ErrorMessage(code=error_code, message=error_msg or "").model_dump()

    return SessionExitedMessage(
        sessionId=message.sessionId, exitCode=exit_code
    ).model_dump()


async def handle_term_in(
    client_id: str, message: ClientMessage
) -> dict[str, Any] | None:
    """Handle term.in message.

    Sends input data to the attached terminal session.

    Args:
        client_id: Unique client identifier.
        message: The client message (TerminalInputMessage).

    Returns:
        None on success, ErrorMessage on failure.
    """
    assert isinstance(message, TerminalInputMessage)

    # Check if client is attached to this session
    conn = get_connection(client_id)
    if not conn or conn.attached_session != message.sessionId:
        return ErrorMessage(
            code=ErrorCodes.NOT_ATTACHED,
            message=f"Not attached to session: {message.sessionId}",
        ).model_dump()

    success, error_code, error_msg = session_manager.send_input(
        message.sessionId, message.data
    )

    if error_code:
        return ErrorMessage(code=error_code, message=error_msg or "").model_dump()

    # No response on success - input is acknowledged implicitly
    return None


async def handle_term_resize(
    client_id: str, message: ClientMessage
) -> dict[str, Any] | None:
    """Handle term.resize message.

    Resizes the terminal to the specified dimensions.

    Args:
        client_id: Unique client identifier.
        message: The client message (TerminalResizeMessage).

    Returns:
        None on success, ErrorMessage on failure.
    """
    assert isinstance(message, TerminalResizeMessage)

    success, error_code, error_msg = session_manager.resize_session(
        message.sessionId, message.cols, message.rows
    )

    if error_code:
        return ErrorMessage(code=error_code, message=error_msg or "").model_dump()

    # No response on success
    return None


async def handle_session_rename(
    client_id: str, message: ClientMessage
) -> dict[str, Any] | None:
    """Handle session.rename message.

    Renames the specified session.

    Args:
        client_id: Unique client identifier.
        message: The client message (SessionRenameMessage).

    Returns:
        SessionRenamedMessage on success, ErrorMessage on failure.
    """
    assert isinstance(message, SessionRenameMessage)

    success = index_store.update_session_name(message.sessionId, message.name)

    if not success:
        return ErrorMessage(
            code=ErrorCodes.SESSION_NOT_FOUND,
            message=f"Session not found: {message.sessionId}",
        ).model_dump()

    return SessionRenamedMessage(
        sessionId=message.sessionId, name=message.name
    ).model_dump()


# Register handlers
dispatcher.register("session.create", handle_session_create)
dispatcher.register("session.attach", handle_session_attach)
dispatcher.register("session.list", handle_session_list)
dispatcher.register("session.terminate", handle_session_terminate)
dispatcher.register("session.rename", handle_session_rename)
dispatcher.register("term.in", handle_term_in)
dispatcher.register("term.resize", handle_term_resize)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for terminal communication.

    Handles WebSocket connections for terminal sessions. Verifies localhost
    connection, manages rate limiting, and dispatches messages to handlers.

    Args:
        websocket: The FastAPI WebSocket connection.

    Returns:
        None. Runs until the connection is closed.
    """
    # Verify localhost connection
    client_host = websocket.client.host if websocket.client else None
    if client_host != "127.0.0.1" and not settings.ALLOW_NON_LOCALHOST:
        await websocket.close(code=1008)
        return

    await websocket.accept()

    # Generate client ID
    client_id = str(uuid.uuid4())

    # Create connection object
    conn = WebSocketConnection(websocket, client_id)
    _connections[client_id] = conn

    # Set up callbacks for session manager
    session_manager.set_output_callback(client_id, conn.handle_output)
    session_manager.set_exit_callback(client_id, conn.handle_exit)

    logger.info("WebSocket connected", extra={"clientId": client_id})

    try:
        # Send server.hello
        hello = ServerHelloMessage(serverTime=utc_now_iso())
        await conn.send_json(hello.model_dump())

        # Message receive loop
        while True:
            # Check rate limit
            if not rate_limiter.check(client_id):
                logger.warning(
                    "Rate limit exceeded",
                    extra={"clientId": client_id},
                )
                await conn.send_json(
                    ErrorMessage(
                        code=ErrorCodes.RATE_LIMIT_EXCEEDED,
                        message="Rate limit exceeded. Maximum 200 messages per second.",
                    ).model_dump()
                )
                await websocket.close(code=1011)
                break

            try:
                raw_message = await websocket.receive_text()
            except WebSocketDisconnect:
                break

            # Dispatch message
            response = await dispatcher.dispatch(client_id, raw_message)

            if response:
                await conn.send_json(response)

                # Close on unknown message type
                if response.get("code") == ErrorCodes.UNKNOWN_MESSAGE_TYPE:
                    await websocket.close(code=1008)
                    break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}", extra={"clientId": client_id}, exc_info=True)
    finally:
        # Cleanup
        _connections.pop(client_id, None)
        session_manager.remove_client_callbacks(client_id)
        session_manager.detach_all_sessions(client_id)
        rate_limiter.cleanup(client_id)

        logger.info("WebSocket disconnected", extra={"clientId": client_id})
