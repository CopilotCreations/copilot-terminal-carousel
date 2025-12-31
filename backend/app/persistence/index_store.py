"""Index store for managing session index.json."""
import json
from pathlib import Path
from typing import Any

from app.util.atomic_write import atomic_write_json, read_json_file
from app.util.paths import get_index_path
from app.util.time import utc_now_iso
from app.ws.protocol import SessionIndexEntry


class IndexStore:
    """Manages the sessions index.json file."""

    PROTOCOL_VERSION = 1

    def __init__(self, index_path: Path | None = None) -> None:
        """Initialize the index store.

        Args:
            index_path: Optional custom path for index.json (for testing)
        """
        self._index_path = index_path or get_index_path()

    @property
    def index_path(self) -> Path:
        """Get the index file path."""
        return self._index_path

    def _get_empty_index(self) -> dict[str, Any]:
        """Create an empty index structure."""
        return {
            "protocolVersion": self.PROTOCOL_VERSION,
            "updatedAt": utc_now_iso(),
            "sessions": [],
        }

    def load(self) -> dict[str, Any]:
        """Load the index from disk.

        Returns:
            Index data dictionary

        Creates empty index if file doesn't exist.
        """
        try:
            return read_json_file(self._index_path)
        except FileNotFoundError:
            return self._get_empty_index()

    def save(self, index: dict[str, Any]) -> None:
        """Save the index to disk atomically.

        Args:
            index: Index data to save
        """
        index["updatedAt"] = utc_now_iso()
        atomic_write_json(self._index_path, index)

    def add_session(
        self,
        session_id: str,
        status: str,
        created_at: str,
        last_activity_at: str,
        name: str | None = None,
    ) -> None:
        """Add a new session to the index.

        Args:
            session_id: Session UUID
            status: Session status (running/exited)
            created_at: ISO timestamp when session was created
            last_activity_at: ISO timestamp of last activity
            name: Optional session name
        """
        index = self.load()
        entry = {
            "sessionId": session_id,
            "status": status,
            "createdAt": created_at,
            "lastActivityAt": last_activity_at,
            "name": name,
        }
        index["sessions"].append(entry)
        self.save(index)

    def update_session_status(
        self,
        session_id: str,
        status: str,
        last_activity_at: str | None = None,
    ) -> None:
        """Update a session's status in the index.

        Args:
            session_id: Session UUID
            status: New status (running/exited)
            last_activity_at: Optional updated last activity timestamp
        """
        index = self.load()
        for session in index["sessions"]:
            if session["sessionId"] == session_id:
                session["status"] = status
                if last_activity_at:
                    session["lastActivityAt"] = last_activity_at
                break
        self.save(index)

    def update_session_name(
        self,
        session_id: str,
        name: str,
    ) -> bool:
        """Update a session's name in the index.

        Args:
            session_id: Session UUID
            name: New session name

        Returns:
            True if session was found and updated, False otherwise
        """
        index = self.load()
        for session in index["sessions"]:
            if session["sessionId"] == session_id:
                session["name"] = name
                self.save(index)
                return True
        return False

    def get_all_sessions(self) -> list[SessionIndexEntry]:
        """Get all sessions from the index.

        Returns:
            List of session index entries, sorted by createdAt descending
        """
        index = self.load()
        sessions = [SessionIndexEntry(**s) for s in index["sessions"]]
        # Sort by createdAt descending
        sessions.sort(key=lambda s: s.createdAt, reverse=True)
        return sessions

    def get_session(self, session_id: str) -> SessionIndexEntry | None:
        """Get a specific session from the index.

        Args:
            session_id: Session UUID

        Returns:
            Session entry or None if not found
        """
        index = self.load()
        for session in index["sessions"]:
            if session["sessionId"] == session_id:
                return SessionIndexEntry(**session)
        return None

    def remove_session(self, session_id: str) -> None:
        """Remove a session from the index.

        Args:
            session_id: Session UUID to remove
        """
        index = self.load()
        index["sessions"] = [
            s for s in index["sessions"] if s["sessionId"] != session_id
        ]
        self.save(index)


# Global index store instance
index_store = IndexStore()
