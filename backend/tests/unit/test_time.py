"""Unit tests for time utilities."""
import pytest
from datetime import datetime, timezone

from app.util.time import utc_now_iso, parse_iso_timestamp


class TestTimeUtilities:
    """Tests for time utility functions."""

    def test_utc_now_iso_format(self) -> None:
        """Test that utc_now_iso returns correct format.

        Validates that the returned timestamp:
            - Ends with 'Z' suffix indicating UTC
            - Has exactly 24 characters
            - Contains proper date/time separators
        """
        ts = utc_now_iso()
        
        assert ts.endswith("Z")
        # Should match pattern: YYYY-MM-DDTHH:MM:SS.sssZ
        assert len(ts) == 24
        assert ts[4] == "-"
        assert ts[7] == "-"
        assert ts[10] == "T"

    def test_utc_now_iso_is_utc(self) -> None:
        """Test that timestamp is in UTC.

        Verifies the generated timestamp represents current UTC time
        by parsing it and comparing to the current datetime.
        """
        ts = utc_now_iso()
        
        # Parse and verify it's close to current time
        parsed = parse_iso_timestamp(ts)
        now = datetime.now(timezone.utc)
        
        diff = abs((now - parsed).total_seconds())
        assert diff < 2  # Within 2 seconds

    def test_parse_iso_timestamp_with_z(self) -> None:
        """Test parsing timestamp with Z suffix.

        Verifies that ISO 8601 timestamps ending with 'Z' (Zulu time)
        are correctly parsed into datetime components.
        """
        ts = "2025-01-01T12:00:00.000Z"
        parsed = parse_iso_timestamp(ts)
        
        assert parsed.year == 2025
        assert parsed.month == 1
        assert parsed.day == 1
        assert parsed.hour == 12
        assert parsed.minute == 0
        assert parsed.second == 0

    def test_parse_iso_timestamp_without_z(self) -> None:
        """Test parsing timestamp without Z suffix.

        Verifies that ISO 8601 timestamps with explicit timezone offset
        (+00:00) are correctly parsed into datetime components.
        """
        ts = "2025-01-01T12:00:00.000+00:00"
        parsed = parse_iso_timestamp(ts)
        
        assert parsed.year == 2025
        assert parsed.month == 1
