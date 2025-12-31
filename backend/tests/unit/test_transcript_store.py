"""Unit tests for transcript store."""
import json
import pytest
from pathlib import Path

from app.persistence.transcript_store import TranscriptStore


class TestTranscriptStore:
    """Tests for TranscriptStore functionality."""

    @pytest.fixture
    def transcript_store(self, tmp_path: Path) -> TranscriptStore:
        """Create a TranscriptStore with a temp path."""
        return TranscriptStore(base_path=tmp_path / "sessions")

    @pytest.fixture
    def session_id(self) -> str:
        """Provide a test session ID."""
        return "12345678-1234-1234-1234-123456789abc"

    def test_init_session(
        self, transcript_store: TranscriptStore, session_id: str
    ) -> None:
        """Test initializing a session creates the transcript file."""
        transcript_store.init_session(session_id)
        transcript_path = transcript_store._get_transcript_path(session_id)
        assert transcript_path.exists()

    def test_append_output_sync(
        self, transcript_store: TranscriptStore, session_id: str
    ) -> None:
        """Test appending output event synchronously."""
        transcript_store.init_session(session_id)
        transcript_store.append_output_sync(session_id, "Hello, world!")

        events = transcript_store.read_all_events(session_id)
        assert len(events) == 1
        assert events[0]["type"] == "out"
        assert events[0]["data"] == "Hello, world!"
        assert events[0]["seq"] == 1

    def test_append_input_sync(
        self, transcript_store: TranscriptStore, session_id: str
    ) -> None:
        """Test appending input event synchronously."""
        transcript_store.init_session(session_id)
        transcript_store.append_input_sync(session_id, "user input\r\n")

        events = transcript_store.read_all_events(session_id)
        assert len(events) == 1
        assert events[0]["type"] == "in"
        assert events[0]["data"] == "user input\r\n"

    def test_append_lifecycle_sync(
        self, transcript_store: TranscriptStore, session_id: str
    ) -> None:
        """Test appending lifecycle event synchronously."""
        transcript_store.init_session(session_id)
        transcript_store.append_lifecycle_sync(
            session_id, "created", {"pid": 12345}
        )

        events = transcript_store.read_all_events(session_id)
        assert len(events) == 1
        assert events[0]["type"] == "lifecycle"
        assert events[0]["event"] == "created"
        assert events[0]["detail"]["pid"] == 12345

    @pytest.mark.asyncio
    async def test_append_output_async(
        self, transcript_store: TranscriptStore, session_id: str
    ) -> None:
        """Test appending output event asynchronously."""
        transcript_store.init_session(session_id)
        await transcript_store.append_output(session_id, "async output")

        events = transcript_store.read_all_events(session_id)
        assert len(events) == 1
        assert events[0]["type"] == "out"
        assert events[0]["data"] == "async output"

    @pytest.mark.asyncio
    async def test_append_input_async(
        self, transcript_store: TranscriptStore, session_id: str
    ) -> None:
        """Test appending input event asynchronously."""
        transcript_store.init_session(session_id)
        await transcript_store.append_input(session_id, "async input")

        events = transcript_store.read_all_events(session_id)
        assert len(events) == 1
        assert events[0]["type"] == "in"

    @pytest.mark.asyncio
    async def test_append_resize(
        self, transcript_store: TranscriptStore, session_id: str
    ) -> None:
        """Test appending resize event."""
        transcript_store.init_session(session_id)
        await transcript_store.append_resize(session_id, 100, 50)

        events = transcript_store.read_all_events(session_id)
        assert len(events) == 1
        assert events[0]["type"] == "resize"
        assert events[0]["cols"] == 100
        assert events[0]["rows"] == 50

    @pytest.mark.asyncio
    async def test_append_lifecycle_async(
        self, transcript_store: TranscriptStore, session_id: str
    ) -> None:
        """Test appending lifecycle event asynchronously."""
        transcript_store.init_session(session_id)
        await transcript_store.append_lifecycle(
            session_id, "exited", {"exitCode": 0}
        )

        events = transcript_store.read_all_events(session_id)
        assert len(events) == 1
        assert events[0]["type"] == "lifecycle"
        assert events[0]["event"] == "exited"

    def test_seq_increments(
        self, transcript_store: TranscriptStore, session_id: str
    ) -> None:
        """Test that sequence numbers increment correctly."""
        transcript_store.init_session(session_id)
        transcript_store.append_output_sync(session_id, "output 1")
        transcript_store.append_input_sync(session_id, "input 1")
        transcript_store.append_output_sync(session_id, "output 2")

        events = transcript_store.read_all_events(session_id)
        assert len(events) == 3
        assert events[0]["seq"] == 1
        assert events[1]["seq"] == 2
        assert events[2]["seq"] == 3

    def test_jsonl_format(
        self, transcript_store: TranscriptStore, session_id: str
    ) -> None:
        """Test that each line is valid JSON."""
        transcript_store.init_session(session_id)
        transcript_store.append_output_sync(session_id, "line 1")
        transcript_store.append_output_sync(session_id, "line 2")

        transcript_path = transcript_store._get_transcript_path(session_id)
        with open(transcript_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        assert len(lines) == 2
        for line in lines:
            # Each line should be valid JSON
            event = json.loads(line.strip())
            assert "ts" in event
            assert "sessionId" in event
            assert "seq" in event
            assert "type" in event

    def test_read_all_events_empty_file(
        self, transcript_store: TranscriptStore, session_id: str
    ) -> None:
        """Test reading from an empty transcript file."""
        transcript_store.init_session(session_id)
        events = transcript_store.read_all_events(session_id)
        assert events == []

    def test_read_all_events_nonexistent(
        self, transcript_store: TranscriptStore
    ) -> None:
        """Test reading from a non-existent transcript returns empty list."""
        events = transcript_store.read_all_events("nonexistent-session-id-1234")
        assert events == []

    def test_event_has_timestamp(
        self, transcript_store: TranscriptStore, session_id: str
    ) -> None:
        """Test that events have proper timestamps."""
        transcript_store.init_session(session_id)
        transcript_store.append_output_sync(session_id, "test")

        events = transcript_store.read_all_events(session_id)
        assert len(events) == 1
        ts = events[0]["ts"]
        assert ts.endswith("Z")
        # Should be ISO format: YYYY-MM-DDTHH:MM:SS.sssZ
        assert "T" in ts

    def test_event_has_session_id(
        self, transcript_store: TranscriptStore, session_id: str
    ) -> None:
        """Test that events include the session ID."""
        transcript_store.init_session(session_id)
        transcript_store.append_output_sync(session_id, "test")

        events = transcript_store.read_all_events(session_id)
        assert events[0]["sessionId"] == session_id

    def test_multiple_sessions_independent(
        self, transcript_store: TranscriptStore
    ) -> None:
        """Test that multiple sessions have independent sequence counters."""
        session1 = "session1-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        session2 = "session2-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

        transcript_store.init_session(session1)
        transcript_store.init_session(session2)

        transcript_store.append_output_sync(session1, "session1 output")
        transcript_store.append_output_sync(session2, "session2 output")

        events1 = transcript_store.read_all_events(session1)
        events2 = transcript_store.read_all_events(session2)

        # Each session should have seq=1
        assert events1[0]["seq"] == 1
        assert events2[0]["seq"] == 1
