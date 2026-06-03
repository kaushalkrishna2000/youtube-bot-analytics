"""Time helpers for channel_lambda."""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:

    # Return the current date and time with UTC timezone awareness
    return datetime.now(timezone.utc)


def utc_iso(value: datetime) -> str:

    # Convert the datetime to ISO format and replace the UTC offset with Z
    return value.isoformat().replace("+00:00", "Z")
