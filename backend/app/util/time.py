"""Utility functions for time handling."""
from datetime import datetime, timezone


def utc_now_iso() -> str:
    """Get current UTC time as ISO-8601 string with millisecond precision.

    Returns:
        str: Current UTC timestamp in format 'YYYY-MM-DDTHH:MM:SS.sssZ'.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def parse_iso_timestamp(ts: str) -> datetime:
    """Parse an ISO-8601 timestamp string to datetime.

    Args:
        ts: ISO-8601 formatted timestamp string, with or without 'Z' suffix.

    Returns:
        datetime: Parsed datetime object with timezone information.
    """
    # Handle both with and without 'Z' suffix
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts)
