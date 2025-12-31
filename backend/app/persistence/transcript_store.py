"""Transcript store for managing session transcript.jsonl files."""
import json
from pathlib import Path
from typing import Any, Literal

import aiofiles

from app.util.paths import get_transcript_path
from app.util.time import utc_now_iso


class TranscriptStore:
    """Manages session transcript.jsonl files with append-only event sourcing."""

    def __init__(self, base_path: Path | None = None) -> None:
        """Initialize the transcript store.

        Args:
            base_path: Optional base path for sessions (for testing)
        """
        self._base_path = base_path
        self._seq_counters: dict[str, int] = {}

    def _get_transcript_path(self, session_id: str) -> Path:
        """Get the transcript.jsonl path for a session."""
        if self._base_path:
            return self._base_path / session_id / "transcript.jsonl"
        return get_transcript_path(session_id)

    def _get_next_seq(self, session_id: str) -> int:
        """Get the next sequence number for a session."""
        if session_id not in self._seq_counters:
            self._seq_counters[session_id] = 0
        self._seq_counters[session_id] += 1
        return self._seq_counters[session_id]

    def _reset_seq(self, session_id: str) -> None:
        """Reset sequence counter for a session (for new sessions)."""
        self._seq_counters[session_id] = 0

    def _create_event(
        self,
        session_id: str,
        event_type: Literal["out", "in", "resize", "lifecycle"],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Create a transcript event.

        Args:
            session_id: Session UUID
            event_type: Type of event
            **kwargs: Additional event-specific fields

        Returns:
            Event dictionary
        """
        return {
            "ts": utc_now_iso(),
            "sessionId": session_id,
            "seq": self._get_next_seq(session_id),
            "type": event_type,
            **kwargs,
        }

    def init_session(self, session_id: str) -> None:
        """Initialize transcript for a new session.

        Args:
            session_id: Session UUID
        """
        self._reset_seq(session_id)
        # Ensure directory exists
        transcript_path = self._get_transcript_path(session_id)
        transcript_path.parent.mkdir(parents=True, exist_ok=True)
        # Create empty file
        transcript_path.touch()

    async def append_output(self, session_id: str, data: str) -> None:
        """Append terminal output event.

        Args:
            session_id: Session UUID
            data: Output data string
        """
        event = self._create_event(session_id, "out", data=data)
        await self._append_event(session_id, event)

    async def append_input(self, session_id: str, data: str) -> None:
        """Append terminal input event.

        Args:
            session_id: Session UUID
            data: Input data string
        """
        event = self._create_event(session_id, "in", data=data)
        await self._append_event(session_id, event)

    async def append_resize(self, session_id: str, cols: int, rows: int) -> None:
        """Append terminal resize event.

        Args:
            session_id: Session UUID
            cols: New column count
            rows: New row count
        """
        event = self._create_event(session_id, "resize", cols=cols, rows=rows)
        await self._append_event(session_id, event)

    async def append_lifecycle(
        self,
        session_id: str,
        lifecycle_event: Literal[
            "created", "attached", "exited", "terminated", "spawn_failed"
        ],
        detail: dict[str, Any] | None = None,
    ) -> None:
        """Append lifecycle event.

        Args:
            session_id: Session UUID
            lifecycle_event: Lifecycle event type
            detail: Optional event-specific details
        """
        event = self._create_event(
            session_id,
            "lifecycle",
            event=lifecycle_event,
            detail=detail or {},
        )
        await self._append_event(session_id, event)

    async def _append_event(self, session_id: str, event: dict[str, Any]) -> None:
        """Append an event to the transcript file.

        Args:
            session_id: Session UUID
            event: Event dictionary to append
        """
        transcript_path = self._get_transcript_path(session_id)
        line = json.dumps(event, ensure_ascii=False) + "\n"
        async with aiofiles.open(transcript_path, "a", encoding="utf-8") as f:
            await f.write(line)

    def append_output_sync(self, session_id: str, data: str) -> None:
        """Synchronously append terminal output event (for non-async contexts).

        Args:
            session_id: Session UUID
            data: Output data string
        """
        event = self._create_event(session_id, "out", data=data)
        self._append_event_sync(session_id, event)

    def append_input_sync(self, session_id: str, data: str) -> None:
        """Synchronously append terminal input event.

        Args:
            session_id: Session UUID
            data: Input data string
        """
        event = self._create_event(session_id, "in", data=data)
        self._append_event_sync(session_id, event)

    def append_lifecycle_sync(
        self,
        session_id: str,
        lifecycle_event: Literal[
            "created", "attached", "exited", "terminated", "spawn_failed"
        ],
        detail: dict[str, Any] | None = None,
    ) -> None:
        """Synchronously append lifecycle event.

        Args:
            session_id: Session UUID
            lifecycle_event: Lifecycle event type
            detail: Optional event-specific details
        """
        event = self._create_event(
            session_id,
            "lifecycle",
            event=lifecycle_event,
            detail=detail or {},
        )
        self._append_event_sync(session_id, event)

    def _append_event_sync(self, session_id: str, event: dict[str, Any]) -> None:
        """Synchronously append an event to the transcript file.

        Args:
            session_id: Session UUID
            event: Event dictionary to append
        """
        transcript_path = self._get_transcript_path(session_id)
        line = json.dumps(event, ensure_ascii=False) + "\n"
        with open(transcript_path, "a", encoding="utf-8") as f:
            f.write(line)

    def read_all_events(self, session_id: str) -> list[dict[str, Any]]:
        """Read all events from a session transcript.

        Args:
            session_id: Session UUID

        Returns:
            List of event dictionaries
        """
        transcript_path = self._get_transcript_path(session_id)
        events = []
        try:
            with open(transcript_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        events.append(json.loads(line))
        except FileNotFoundError:
            pass
        return events


# Global transcript store instance
transcript_store = TranscriptStore()
