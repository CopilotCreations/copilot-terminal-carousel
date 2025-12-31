"""Meta store for managing session meta.json files."""
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.util.atomic_write import atomic_write_json, read_json_file
from app.util.paths import get_meta_path
from app.util.time import utc_now_iso


class SessionMeta(BaseModel):
    """Session metadata model."""

    sessionId: str
    status: str  # "running" | "exited"
    createdAt: str
    lastActivityAt: str
    workspacePath: str
    pid: int | None
    cols: int
    rows: int
    exitCode: int | None = None
    copilotPath: str
    error: dict[str, str] | None = None


class MetaStore:
    """Manages session meta.json files."""

    def __init__(self, base_path: Path | None = None) -> None:
        """Initialize the meta store.

        Args:
            base_path: Optional base path for sessions (for testing)
        """
        self._base_path = base_path

    def _get_meta_path(self, session_id: str) -> Path:
        """Get the meta.json path for a session."""
        if self._base_path:
            return self._base_path / session_id / "meta.json"
        return get_meta_path(session_id)

    def load(self, session_id: str) -> SessionMeta | None:
        """Load session metadata from disk.

        Args:
            session_id: Session UUID

        Returns:
            SessionMeta or None if not found
        """
        meta_path = self._get_meta_path(session_id)
        try:
            data = read_json_file(meta_path)
            return SessionMeta(**data)
        except FileNotFoundError:
            return None

    def save(self, meta: SessionMeta) -> None:
        """Save session metadata to disk atomically.

        Args:
            meta: Session metadata to save
        """
        meta_path = self._get_meta_path(meta.sessionId)
        atomic_write_json(meta_path, meta.model_dump())

    def create(
        self,
        session_id: str,
        workspace_path: str,
        copilot_path: str,
        pid: int | None,
        cols: int,
        rows: int,
        error: dict[str, str] | None = None,
    ) -> SessionMeta:
        """Create new session metadata.

        Args:
            session_id: Session UUID
            workspace_path: Absolute path to workspace directory
            copilot_path: Path to copilot executable
            pid: Process ID or None if spawn failed
            cols: Initial terminal columns
            rows: Initial terminal rows
            error: Error info if spawn failed

        Returns:
            Created SessionMeta
        """
        now = utc_now_iso()
        status = "exited" if error else "running"

        meta = SessionMeta(
            sessionId=session_id,
            status=status,
            createdAt=now,
            lastActivityAt=now,
            workspacePath=workspace_path,
            pid=pid,
            cols=cols,
            rows=rows,
            copilotPath=copilot_path,
            error=error,
        )
        self.save(meta)
        return meta

    def update_activity(self, session_id: str) -> None:
        """Update the last activity timestamp.

        Args:
            session_id: Session UUID
        """
        meta = self.load(session_id)
        if meta:
            meta.lastActivityAt = utc_now_iso()
            self.save(meta)

    def update_status(
        self,
        session_id: str,
        status: str,
        exit_code: int | None = None,
    ) -> None:
        """Update session status.

        Args:
            session_id: Session UUID
            status: New status
            exit_code: Exit code if exited
        """
        meta = self.load(session_id)
        if meta:
            meta.status = status
            meta.lastActivityAt = utc_now_iso()
            if exit_code is not None:
                meta.exitCode = exit_code
            self.save(meta)

    def update_dimensions(
        self,
        session_id: str,
        cols: int,
        rows: int,
    ) -> None:
        """Update terminal dimensions.

        Args:
            session_id: Session UUID
            cols: New column count
            rows: New row count
        """
        meta = self.load(session_id)
        if meta:
            meta.cols = cols
            meta.rows = rows
            meta.lastActivityAt = utc_now_iso()
            self.save(meta)


# Global meta store instance
meta_store = MetaStore()
