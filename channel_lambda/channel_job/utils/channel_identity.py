"""Channel input normalization and identity parsing."""

from __future__ import annotations

import re
import uuid
from typing import Any
from urllib.parse import urlparse


CHANNEL_ID_RE = re.compile(r"^UC[\w-]{22}$")
HANDLE_RE = re.compile(r"^@([\w.-]+)$", re.IGNORECASE)


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------


def get_job_id(context: Any) -> str:

    # Return the AWS request ID if available, otherwise generate a unique UUID
    return getattr(context, "aws_request_id", None) or uuid.uuid4().hex


def normalize_channel_inputs(values: list[str]) -> list[str]:

    # Initialize a set to track already processed channel identifiers
    seen: set[str] = set()

    # Create a list to store the unique normalized results
    normalized: list[str] = []

    # Iterate through each raw input value provided
    for value in values:

        # Remove leading and trailing whitespace from the input
        cleaned = value.strip()

        # Skip empty strings after trimming
        if not cleaned:
            continue

        # Use lowercase version for case-insensitive duplicate checking
        dedupe_key = cleaned.lower()

        # Skip if we have already encountered this channel identifier
        if dedupe_key in seen:
            continue

        # Mark this identifier as seen
        seen.add(dedupe_key)

        # Append the cleaned original version to our results
        normalized.append(cleaned)

    # Return the ordered list of unique channel inputs
    return normalized


# -----------------------------------------------------------------------------
# Private Helpers
# -----------------------------------------------------------------------------


def extract_channel_from_url(raw: str) -> str | None:

    # Parse the raw URL string into its component parts
    parsed = urlparse(raw.strip())

    # Extract and clean the URL path component
    path = parsed.path.strip("/")

    # Return None if the URL path is empty
    if not path:
        return None

    # Split the path into segments to identify the channel token
    parts = path.split("/")

    # Identify legacy channel markers and extract the identifier
    if parts[0] in ("channel", "c", "user") and len(parts) >= 2:

        # Return the direct channel ID or a marked legacy identifier
        return parts[1] if parts[0] == "channel" else f"legacy:{parts[0]}:{parts[1]}"

    # Extract handles if the path starts with the @ symbol
    if parts[0].startswith("@"):

        # Return the handle segment including the @ prefix
        return parts[0]

    # Return None if the URL structure is unrecognized
    return None


def parse_int_or_none(value: object) -> int | None:

    # Attempt to convert the provided value to an integer
    try:

        # Return the integer value if not empty or None
        return int(value) if value not in (None, "") else None

    # Return None if conversion fails due to type or value errors
    except (TypeError, ValueError):

        # Suppress errors and return a safe default
        return None
