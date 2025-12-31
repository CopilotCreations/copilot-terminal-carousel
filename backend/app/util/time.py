"""Utility functions for time handling."""
from datetime import datetime, timezone


def utc_now_iso() -> str:
    """Get current UTC time as ISO-8601 string with millisecond precision."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def parse_iso_timestamp(ts: str) -> datetime:
    """Parse an ISO-8601 timestamp string to datetime."""
    # Handle both with and without 'Z' suffix
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts)
