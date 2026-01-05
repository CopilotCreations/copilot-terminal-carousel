"""Session manager for tracking and managing terminal sessions."""
import asyncio
import uuid
from pathlib import Path
from typing import Any, Callable

from app.config import settings
from app.logging_setup import get_logger
from app.persistence.index_store import index_store
from app.persistence.meta_store import meta_store, SessionMeta
from app.persistence.transcript_store import transcript_store
from app.sessions.pty_process import PtyProcess, create_pty_process
from app.util.paths import ensure_session_directories, get_workspace_path
from app.util.time import utc_now_iso
from app.ws.protocol import ErrorCodes, SessionInfo, SessionIndexEntry

logger = get_logger(__name__)


class Session:
    """Represents an active terminal session."""

    def __init__(
        self,
        session_id: str,
        pty: PtyProcess,
        meta: SessionMeta,
    ) -> None:
        """Initialize session.

        Args:
            session_id: Session UUID
            pty: PTY process instance
            meta: Session metadata
        """
        self.session_id = session_id
        self.pty = pty
        self.meta = meta
        self.attached_clients: set[str] = set()

    @property
    def is_running(self) -> bool:
        """Check if session is running.

        Returns:
            bool: True if the PTY process is running, False otherwise.
        """
        return self.pty.is_running

    def to_session_info(self) -> SessionInfo:
        """Convert session to SessionInfo for API responses.

        Returns:
            SessionInfo: A data transfer object containing session details
                including status, timestamps, workspace path, and process info.
        """
        return SessionInfo(
            sessionId=self.session_id,
            status="running" if self.is_running else "exited",
            createdAt=self.meta.createdAt,
            lastActivityAt=self.meta.lastActivityAt,
            workspacePath=self.meta.workspacePath,
            pid=self.pty.pid,
            cols=self.pty.cols,
            rows=self.pty.rows,
            exitCode=self.pty.exit_code,
            copilotPath=self.meta.copilotPath,
            error=self.meta.error,
        )


class SessionManager:
    """Manages all terminal sessions."""

    def __init__(self, use_mock_pty: bool = False) -> None:
        """Initialize session manager.

        Args:
            use_mock_pty: Use mock PTY for testing
        """
        self._sessions: dict[str, Session] = {}
        self._use_mock_pty = use_mock_pty
        self._output_callbacks: dict[str, Callable[[str, str], Any]] = {}
        self._exit_callbacks: dict[str, Callable[[str, int | None], Any]] = {}
        self._lock = asyncio.Lock()

    @property
    def running_session_count(self) -> int:
        """Get count of currently running sessions.

        Returns:
            int: Number of sessions with active PTY processes.
        """
        return sum(1 for s in self._sessions.values() if s.is_running)

    def set_output_callback(
        self, client_id: str, callback: Callable[[str, str], Any]
    ) -> None:
        """Set output callback for a client.

        Registers a callback function that will be invoked when terminal
        output is received from any session the client is attached to.

        Args:
            client_id: Unique identifier for the WebSocket client.
            callback: Callback function that receives (session_id, data)
                where session_id is the UUID and data is the terminal output.
        """
        self._output_callbacks[client_id] = callback

    def set_exit_callback(
        self, client_id: str, callback: Callable[[str, int | None], Any]
    ) -> None:
        """Set exit callback for a client.

        Registers a callback function that will be invoked when a session's
        PTY process exits.

        Args:
            client_id: Unique identifier for the WebSocket client.
            callback: Callback function that receives (session_id, exit_code)
                where exit_code may be None if the process was killed.
        """
        self._exit_callbacks[client_id] = callback

    def remove_client_callbacks(self, client_id: str) -> None:
        """Remove all callbacks for a client.

        Cleans up both output and exit callbacks when a client disconnects.

        Args:
            client_id: Unique identifier for the WebSocket client to remove.
        """
        self._output_callbacks.pop(client_id, None)
        self._exit_callbacks.pop(client_id, None)

    async def _on_pty_output(self, session_id: str, data: str) -> None:
        """Handle PTY output from a terminal session.

        Appends output to the transcript, updates activity timestamp, and
        notifies all attached clients via their registered callbacks.

        Args:
            session_id: UUID of the session that produced output.
            data: Raw terminal output data string.
        """
        session = self._sessions.get(session_id)
        if not session:
            return

        # Append to transcript
        await transcript_store.append_output(session_id, data)

        # Update last activity
        meta_store.update_activity(session_id)

        # Notify attached clients
        for client_id in session.attached_clients:
            callback = self._output_callbacks.get(client_id)
            if callback:
                try:
                    result = callback(session_id, data)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    logger.error(f"Output callback error: {e}")

    async def _on_pty_exit(self, session_id: str, exit_code: int | None) -> None:
        """Handle PTY process exit.

        Updates session status in persistence stores, logs the exit event,
        and notifies all attached clients via their registered callbacks.

        Args:
            session_id: UUID of the session whose process exited.
            exit_code: Process exit code, or None if terminated abnormally.
        """
        session = self._sessions.get(session_id)
        if not session:
            return

        # Update persistence
        meta_store.update_status(session_id, "exited", exit_code)
        index_store.update_session_status(session_id, "exited", utc_now_iso())
        await transcript_store.append_lifecycle(
            session_id, "exited", {"exitCode": exit_code}
        )

        # Notify attached clients
        for client_id in list(session.attached_clients):
            callback = self._exit_callbacks.get(client_id)
            if callback:
                try:
                    result = callback(session_id, exit_code)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    logger.error(f"Exit callback error: {e}")

    async def create_session(
        self,
        copilot_path: str | None = None,
    ) -> tuple[Session | None, str | None, str | None]:
        """Create a new terminal session.

        Creates a new PTY process, initializes the workspace directory,
        sets up transcript storage, and starts the copilot executable.

        Args:
            copilot_path: Optional path to copilot executable. If None,
                uses the default path from settings.

        Returns:
            tuple[Session | None, str | None, str | None]: A tuple containing:
                - Session object if successful, None on failure.
                - Error code string if failed, None on success.
                - Error message string if failed, None on success.
        """
        async with self._lock:
            # Check max sessions
            if self.running_session_count >= settings.MAX_SESSIONS:
                return (
                    None,
                    ErrorCodes.MAX_SESSIONS_REACHED,
                    f"Maximum running sessions ({settings.MAX_SESSIONS}) reached.",
                )

            # Generate session ID
            session_id = str(uuid.uuid4())

            # Create directories
            workspace_path = ensure_session_directories(session_id)

            # Initialize transcript
            transcript_store.init_session(session_id)

            # Create PTY process
            pty = create_pty_process(
                session_id=session_id,
                workspace_path=workspace_path,
                cols=settings.INITIAL_COLS,
                rows=settings.INITIAL_ROWS,
                on_output=self._on_pty_output,
                on_exit=self._on_pty_exit,
                use_mock=self._use_mock_pty,
            )

            # Spawn process
            exe_path = copilot_path or settings.COPILOT_PATH
            success, error_msg = pty.spawn(exe_path)

            if not success:
                # Create session metadata with error
                meta = meta_store.create(
                    session_id=session_id,
                    workspace_path=str(workspace_path.absolute()),
                    copilot_path=exe_path,
                    pid=None,
                    cols=settings.INITIAL_COLS,
                    rows=settings.INITIAL_ROWS,
                    error={"code": "SPAWN_FAILED", "message": error_msg or "Unknown error"},
                )

                # Add to index
                index_store.add_session(
                    session_id=session_id,
                    status="exited",
                    created_at=meta.createdAt,
                    last_activity_at=meta.lastActivityAt,
                )

                # Log spawn failure
                await transcript_store.append_lifecycle(
                    session_id, "spawn_failed", {"error": error_msg}
                )

                return (
                    None,
                    ErrorCodes.SPAWN_FAILED,
                    f"Failed to start copilot.exe: {error_msg}",
                )

            # Create session metadata
            meta = meta_store.create(
                session_id=session_id,
                workspace_path=str(workspace_path.absolute()),
                copilot_path=exe_path,
                pid=pty.pid,
                cols=settings.INITIAL_COLS,
                rows=settings.INITIAL_ROWS,
            )

            # Add to index
            index_store.add_session(
                session_id=session_id,
                status="running",
                created_at=meta.createdAt,
                last_activity_at=meta.lastActivityAt,
            )

            # Log creation
            await transcript_store.append_lifecycle(
                session_id, "created", {"pid": pty.pid}
            )

            # Create session object
            session = Session(session_id=session_id, pty=pty, meta=meta)
            self._sessions[session_id] = session

            # Start read loop
            await pty.start_read_loop()

            logger.info(
                "Session created",
                extra={
                    "sessionId": session_id,
                    "pid": pty.pid,
                    "workspacePath": str(workspace_path),
                },
            )

            return session, None, None

    def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID.

        Args:
            session_id: UUID of the session to retrieve.

        Returns:
            Session | None: The session object if found, None otherwise.
        """
        return self._sessions.get(session_id)

    async def attach_session(
        self, session_id: str, client_id: str
    ) -> tuple[Session | None, str | None, str | None]:
        """Attach a client to a session.

        Associates a WebSocket client with a session so it receives
        output and exit notifications. Logs the attachment event.

        Args:
            session_id: UUID of the session to attach to.
            client_id: Unique identifier for the WebSocket client.

        Returns:
            tuple[Session | None, str | None, str | None]: A tuple containing:
                - Session object if successful, None on failure.
                - Error code string if failed, None on success.
                - Error message string if failed, None on success.
        """
        session = self._sessions.get(session_id)

        if not session:
            # Check if session exists in persistence
            meta = meta_store.load(session_id)
            if not meta:
                return (
                    None,
                    ErrorCodes.SESSION_NOT_FOUND,
                    f"Session does not exist: {session_id}",
                )

            # Session exists but is not running (was persisted but server restarted)
            # Return error for now - could implement session restoration later
            return (
                None,
                ErrorCodes.SESSION_NOT_FOUND,
                f"Session does not exist: {session_id}",
            )

        session.attached_clients.add(client_id)

        # Log attach
        await transcript_store.append_lifecycle(
            session_id, "attached", {"clientId": client_id}
        )

        logger.info(
            "Client attached to session",
            extra={"sessionId": session_id, "clientId": client_id},
        )

        return session, None, None

    def detach_session(self, session_id: str, client_id: str) -> None:
        """Detach a client from a session.

        Removes the client from the session's attached clients set so it
        no longer receives output or exit notifications from that session.

        Args:
            session_id: UUID of the session to detach from.
            client_id: Unique identifier for the WebSocket client.
        """
        session = self._sessions.get(session_id)
        if session:
            session.attached_clients.discard(client_id)

    def detach_all_sessions(self, client_id: str) -> None:
        """Detach a client from all sessions.

        Removes the client from all sessions' attached clients sets.
        Typically called when a WebSocket client disconnects.

        Args:
            client_id: Unique identifier for the WebSocket client.
        """
        for session in self._sessions.values():
            session.attached_clients.discard(client_id)

    async def terminate_session(
        self, session_id: str
    ) -> tuple[int | None, str | None, str | None]:
        """Terminate a session.

        Stops the PTY process, updates persistence stores with the final
        status, and logs the termination event.

        Args:
            session_id: UUID of the session to terminate.

        Returns:
            tuple[int | None, str | None, str | None]: A tuple containing:
                - Exit code of the terminated process, or None.
                - Error code string if failed, None on success.
                - Error message string if failed, None on success.
        """
        session = self._sessions.get(session_id)

        if not session:
            return None, ErrorCodes.SESSION_NOT_FOUND, f"Session does not exist: {session_id}"

        # Stop PTY
        await session.pty.stop()

        # Update persistence
        exit_code = session.pty.exit_code
        meta_store.update_status(session_id, "exited", exit_code)
        index_store.update_session_status(session_id, "exited", utc_now_iso())

        # Log termination
        await transcript_store.append_lifecycle(
            session_id, "terminated", {"exitCode": exit_code}
        )

        logger.info(
            "Session terminated",
            extra={"sessionId": session_id, "exitCode": exit_code},
        )

        return exit_code, None, None

    def send_input(
        self, session_id: str, data: str
    ) -> tuple[bool, str | None, str | None]:
        """Send input to a session's terminal.

        Validates input size, writes data to the PTY, logs the input
        to the transcript, and updates the activity timestamp.

        Args:
            session_id: UUID of the session to send input to.
            data: Input string to write to the terminal.

        Returns:
            tuple[bool, str | None, str | None]: A tuple containing:
                - True if input was sent successfully, False otherwise.
                - Error code string if failed, None on success.
                - Error message string if failed, None on success.
        """
        # Validate input size
        if len(data) > settings.MAX_INPUT_CHARS_PER_MESSAGE:
            return (
                False,
                ErrorCodes.INPUT_TOO_LARGE,
                f"Input exceeds {settings.MAX_INPUT_CHARS_PER_MESSAGE} characters.",
            )

        session = self._sessions.get(session_id)
        if not session:
            return False, ErrorCodes.SESSION_NOT_FOUND, f"Session does not exist: {session_id}"

        if not session.is_running:
            return False, "SESSION_NOT_RUNNING", "Session is not running"

        # Write to PTY
        session.pty.write(data)

        # Log input (sync to avoid blocking)
        transcript_store.append_input_sync(session_id, data)

        # Update activity
        meta_store.update_activity(session_id)

        return True, None, None

    def resize_session(
        self, session_id: str, cols: int, rows: int
    ) -> tuple[bool, str | None, str | None]:
        """Resize a session's terminal dimensions.

        Validates the new dimensions against configured bounds, resizes
        the PTY, and updates the dimensions in persistence.

        Args:
            session_id: UUID of the session to resize.
            cols: New column count (must be within MIN_COLS to MAX_COLS).
            rows: New row count (must be within MIN_ROWS to MAX_ROWS).

        Returns:
            tuple[bool, str | None, str | None]: A tuple containing:
                - True if resize was successful, False otherwise.
                - Error code string if failed, None on success.
                - Error message string if failed, None on success.
        """
        # Validate bounds
        if not (settings.MIN_COLS <= cols <= settings.MAX_COLS):
            return (
                False,
                ErrorCodes.INVALID_RESIZE,
                f"cols must be {settings.MIN_COLS}-{settings.MAX_COLS} and rows must be {settings.MIN_ROWS}-{settings.MAX_ROWS}.",
            )
        if not (settings.MIN_ROWS <= rows <= settings.MAX_ROWS):
            return (
                False,
                ErrorCodes.INVALID_RESIZE,
                f"cols must be {settings.MIN_COLS}-{settings.MAX_COLS} and rows must be {settings.MIN_ROWS}-{settings.MAX_ROWS}.",
            )

        session = self._sessions.get(session_id)
        if not session:
            return False, ErrorCodes.SESSION_NOT_FOUND, f"Session does not exist: {session_id}"

        # Resize PTY
        if not session.pty.resize(cols, rows):
            return False, "RESIZE_FAILED", "Failed to resize terminal"

        # Update persistence
        meta_store.update_dimensions(session_id, cols, rows)

        return True, None, None

    def list_sessions(self) -> list[SessionIndexEntry]:
        """List all sessions from the index store.

        Returns:
            list[SessionIndexEntry]: List of session index entries containing
                session IDs, statuses, and timestamps for all known sessions.
        """
        return index_store.get_all_sessions()

    async def shutdown(self) -> None:
        """Shutdown all sessions gracefully.

        Terminates all active sessions and clears the session dictionary.
        Errors during individual session termination are logged but do not
        prevent other sessions from being terminated.
        """
        for session_id in list(self._sessions.keys()):
            try:
                await self.terminate_session(session_id)
            except Exception as e:
                logger.error(f"Error shutting down session {session_id}: {e}")

        self._sessions.clear()


# Global session manager instance
session_manager = SessionManager()
