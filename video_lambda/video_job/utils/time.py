"""Time helpers for video_lambda."""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return the current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def utc_iso(value: datetime) -> str:
    """Format a datetime as an ISO-8601 UTC string ending in ``Z``."""
    return value.isoformat().replace("+00:00", "Z")
