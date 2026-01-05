"""PTY process management using pywinpty for Windows ConPTY."""
import asyncio
import logging
from typing import Callable, Any
from pathlib import Path

try:
    import winpty
    WINPTY_AVAILABLE = True
except ImportError:
    WINPTY_AVAILABLE = False

from app.config import settings
from app.logging_setup import get_logger

logger = get_logger(__name__)


class PtyProcess:
    """Wrapper for a PTY process running copilot.exe."""

    def __init__(
        self,
        session_id: str,
        workspace_path: Path,
        cols: int,
        rows: int,
        on_output: Callable[[str, str], Any] | None = None,
        on_exit: Callable[[str, int | None], Any] | None = None,
    ) -> None:
        """Initialize PTY process.

        Args:
            session_id: Session UUID
            workspace_path: Working directory for the process
            cols: Initial terminal columns
            rows: Initial terminal rows
            on_output: Callback for output data (session_id, data)
            on_exit: Callback when process exits (session_id, exit_code)
        """
        self.session_id = session_id
        self.workspace_path = workspace_path
        self.cols = cols
        self.rows = rows
        self.on_output = on_output
        self.on_exit = on_exit

        self._pty: Any = None
        self._pid: int | None = None
        self._running = False
        self._read_task: asyncio.Task[None] | None = None
        self._exit_code: int | None = None

    @property
    def pid(self) -> int | None:
        """Get the process ID.

        Returns:
            The process ID if the process has been spawned, None otherwise.
        """
        return self._pid

    @property
    def is_running(self) -> bool:
        """Check if the process is running.

        Returns:
            True if the process is currently running, False otherwise.
        """
        return self._running

    @property
    def exit_code(self) -> int | None:
        """Get the exit code if process has exited.

        Returns:
            The exit code if the process has exited, None if still running
            or exit code is unavailable.
        """
        return self._exit_code

    def spawn(self, copilot_path: str | None = None) -> tuple[bool, str | None]:
        """Spawn the PTY process.

        Args:
            copilot_path: Path to copilot executable (defaults to settings)

        Returns:
            Tuple of (success, error_message)
        """
        if not WINPTY_AVAILABLE:
            return False, "pywinpty is not available on this system"

        exe_path = copilot_path or settings.COPILOT_PATH

        try:
            # Ensure workspace exists
            self.workspace_path.mkdir(parents=True, exist_ok=True)

            # Spawn PTY with copilot
            self._pty = winpty.PtyProcess.spawn(
                exe_path,
                cwd=str(self.workspace_path),
                dimensions=(self.rows, self.cols),
            )
            self._pid = self._pty.pid
            self._running = True

            logger.info(
                f"Spawned PTY process",
                extra={
                    "sessionId": self.session_id,
                    "pid": self._pid,
                    "copilotPath": exe_path,
                },
            )

            return True, None

        except FileNotFoundError:
            error_msg = f"Executable not found: {exe_path}"
            logger.error(error_msg, extra={"sessionId": self.session_id})
            return False, error_msg
        except Exception as e:
            error_msg = f"Failed to spawn PTY: {str(e)}"
            logger.error(error_msg, extra={"sessionId": self.session_id})
            return False, error_msg

    async def start_read_loop(self) -> None:
        """Start the async read loop for PTY output.

        Creates an asyncio task that continuously reads from the PTY and
        invokes the on_output callback with any data received. Does nothing
        if the PTY is not spawned or not running.
        """
        if not self._pty or not self._running:
            return

        self._read_task = asyncio.create_task(self._read_loop())

    async def _read_loop(self) -> None:
        """Continuously read from PTY and call output callback.

        Runs in a loop reading PTY output in a thread executor to avoid
        blocking the event loop. Exits when the process terminates or
        an error occurs, then calls _handle_exit.
        """
        loop = asyncio.get_event_loop()

        while self._running and self._pty:
            try:
                # Read in thread pool to avoid blocking
                data = await loop.run_in_executor(None, self._read_pty)
                if data:
                    if self.on_output:
                        await self._call_async_or_sync(
                            self.on_output, self.session_id, data
                        )
                else:
                    # Empty read usually means process exited
                    await asyncio.sleep(0.01)

            except EOFError:
                # Process exited
                break
            except Exception as e:
                logger.error(
                    f"PTY read error: {e}",
                    extra={"sessionId": self.session_id},
                )
                break

        await self._handle_exit()

    def _read_pty(self) -> str:
        """Read from PTY (blocking, called in executor).

        Returns:
            Data read from the PTY as a string.

        Raises:
            EOFError: If the PTY is not available or the process is not alive.
        """
        if not self._pty or not self._pty.isalive():
            raise EOFError()

        try:
            return self._pty.read(4096)
        except Exception:
            if not self._pty.isalive():
                raise EOFError()
            raise

    async def _handle_exit(self) -> None:
        """Handle process exit.

        Sets the running flag to False, captures the exit code from the PTY,
        logs the exit event, and invokes the on_exit callback if provided.
        """
        self._running = False

        if self._pty:
            try:
                self._exit_code = self._pty.exitstatus
            except Exception:
                self._exit_code = None

        logger.info(
            f"PTY process exited",
            extra={
                "sessionId": self.session_id,
                "exitCode": self._exit_code,
            },
        )

        if self.on_exit:
            await self._call_async_or_sync(
                self.on_exit, self.session_id, self._exit_code
            )

    async def _call_async_or_sync(
        self, callback: Callable[..., Any], *args: Any
    ) -> Any:
        """Call a callback that may be async or sync.

        Args:
            callback: The callback function to invoke.
            *args: Arguments to pass to the callback.

        Returns:
            The result of the callback invocation.
        """
        result = callback(*args)
        if asyncio.iscoroutine(result):
            return await result
        return result

    def write(self, data: str) -> None:
        """Write input to PTY stdin.

        Args:
            data: Input string to write
        """
        if not self._pty or not self._running:
            logger.warning(
                "Attempted to write to non-running PTY",
                extra={"sessionId": self.session_id},
            )
            return

        try:
            self._pty.write(data)
        except Exception as e:
            logger.error(
                f"PTY write error: {e}",
                extra={"sessionId": self.session_id},
            )

    def resize(self, cols: int, rows: int) -> bool:
        """Resize the PTY.

        Args:
            cols: New column count
            rows: New row count

        Returns:
            True if resize succeeded
        """
        if not self._pty or not self._running:
            return False

        try:
            self._pty.setwinsize(rows, cols)
            self.cols = cols
            self.rows = rows
            logger.debug(
                f"PTY resized",
                extra={
                    "sessionId": self.session_id,
                    "cols": cols,
                    "rows": rows,
                },
            )
            return True
        except Exception as e:
            logger.error(
                f"PTY resize error: {e}",
                extra={"sessionId": self.session_id},
            )
            return False

    def terminate(self) -> None:
        """Terminate the PTY process.

        Forcefully terminates the PTY process if it is still alive and
        sets the running flag to False. Does nothing if the PTY is not
        initialized.
        """
        if not self._pty:
            return

        try:
            if self._pty.isalive():
                self._pty.terminate(force=True)
            self._running = False
            logger.info(
                "PTY process terminated",
                extra={"sessionId": self.session_id},
            )
        except Exception as e:
            logger.error(
                f"PTY terminate error: {e}",
                extra={"sessionId": self.session_id},
            )

    async def stop(self) -> None:
        """Stop the PTY process and cleanup.

        Terminates the PTY process, cancels the read task if running,
        and cleans up internal state by setting the PTY reference to None.
        """
        self.terminate()

        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass

        self._pty = None


class MockPtyProcess(PtyProcess):
    """Mock PTY process for testing without real PTY."""

    def __init__(
        self,
        session_id: str,
        workspace_path: Path,
        cols: int,
        rows: int,
        on_output: Callable[[str, str], Any] | None = None,
        on_exit: Callable[[str, int | None], Any] | None = None,
    ) -> None:
        """Initialize mock PTY process.

        Args:
            session_id: Session UUID.
            workspace_path: Working directory for the process.
            cols: Initial terminal columns.
            rows: Initial terminal rows.
            on_output: Callback for output data (session_id, data).
            on_exit: Callback when process exits (session_id, exit_code).
        """
        super().__init__(
            session_id, workspace_path, cols, rows, on_output, on_exit
        )
        self._input_buffer: list[str] = []
        self._mock_exit_code = 0

    def spawn(self, copilot_path: str | None = None) -> tuple[bool, str | None]:
        """Spawn mock PTY process.

        Args:
            copilot_path: Path to copilot executable (ignored in mock).

        Returns:
            Tuple of (success, error_message). Always succeeds for mock.
        """
        self._pid = 99999
        self._running = True
        logger.info(
            "Spawned mock PTY process",
            extra={"sessionId": self.session_id, "pid": self._pid},
        )
        return True, None

    async def start_read_loop(self) -> None:
        """Start mock read loop that echoes input.

        Creates an asyncio task that sends a welcome message and echoes
        any input written to the mock PTY.
        """
        self._read_task = asyncio.create_task(self._mock_read_loop())

    async def _mock_read_loop(self) -> None:
        """Mock read loop that sends welcome message and echoes input.

        Sends an initial welcome message, then continuously checks the
        input buffer and echoes any buffered input back via the on_output
        callback.
        """
        # Send welcome message
        if self.on_output:
            await self._call_async_or_sync(
                self.on_output,
                self.session_id,
                "Welcome to Copilot Terminal (Mock Mode)\r\n$ ",
            )

        while self._running:
            await asyncio.sleep(0.1)
            if self._input_buffer:
                data = self._input_buffer.pop(0)
                if self.on_output:
                    # Echo input back
                    await self._call_async_or_sync(
                        self.on_output,
                        self.session_id,
                        f"{data}\r\n$ ",
                    )

    def write(self, data: str) -> None:
        """Buffer input for echo.

        Args:
            data: Input string to buffer for echoing.
        """
        if self._running:
            self._input_buffer.append(data)

    def resize(self, cols: int, rows: int) -> bool:
        """Resize the mock PTY.

        Args:
            cols: New column count
            rows: New row count

        Returns:
            True if resize succeeded
        """
        if not self._running:
            return False
        self.cols = cols
        self.rows = rows
        return True

    def terminate(self) -> None:
        """Terminate mock process.

        Sets the running flag to False and captures the mock exit code.
        """
        self._running = False
        self._exit_code = self._mock_exit_code


def create_pty_process(
    session_id: str,
    workspace_path: Path,
    cols: int,
    rows: int,
    on_output: Callable[[str, str], Any] | None = None,
    on_exit: Callable[[str, int | None], Any] | None = None,
    use_mock: bool = False,
) -> PtyProcess:
    """Factory function to create PTY process.

    Args:
        session_id: Session UUID
        workspace_path: Working directory
        cols: Initial columns
        rows: Initial rows
        on_output: Output callback
        on_exit: Exit callback
        use_mock: Use mock PTY for testing

    Returns:
        PtyProcess instance
    """
    if use_mock or not WINPTY_AVAILABLE:
        return MockPtyProcess(
            session_id, workspace_path, cols, rows, on_output, on_exit
        )
    return PtyProcess(
        session_id, workspace_path, cols, rows, on_output, on_exit
    )
