"""Channel input normalization and identity parsing."""

from __future__ import annotations

import re
import uuid
from typing import Any
from urllib.parse import urlparse


CHANNEL_ID_RE = re.compile(r"^UC[\w-]{22}$")
HANDLE_RE = re.compile(r"^@([\w.-]+)$", re.IGNORECASE)


def get_job_id(context: Any) -> str:
    """Return the AWS request ID or a generated local-run ID."""
    return getattr(context, "aws_request_id", None) or uuid.uuid4().hex


def normalize_channel_inputs(values: list[str]) -> list[str]:
    """Trim and deduplicate configured channel inputs while preserving order.

    Args:
        values: Raw channel inputs from environment or code settings.

    Returns:
        Cleaned channel inputs with case-insensitive duplicates removed.
    """
    seen: set[str] = set()
    normalized: list[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned:
            continue
        dedupe_key = cleaned.lower()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        normalized.append(cleaned)
    return normalized


def extract_channel_from_url(raw: str) -> str | None:
    """Extract a channel identifier token from a YouTube channel URL.

    Args:
        raw: Raw YouTube URL supplied as a channel input.

    Returns:
        Channel ID, ``@handle``, legacy marker, or ``None`` when the URL shape
        is not recognized.
    """
    parsed = urlparse(raw.strip())
    path = parsed.path.strip("/")
    if not path:
        return None
    parts = path.split("/")
    # Legacy /c/... and /user/... paths need a second resolver step because
    # they are not canonical channel IDs.
    if parts[0] in ("channel", "c", "user") and len(parts) >= 2:
        return parts[1] if parts[0] == "channel" else f"legacy:{parts[0]}:{parts[1]}"
    if parts[0].startswith("@"):
        return parts[0]
    return None


def parse_int_or_none(value: object) -> int | None:
    """Parse an optional integer value from YouTube statistics."""
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None
