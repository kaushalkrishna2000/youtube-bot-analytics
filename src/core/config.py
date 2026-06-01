"""Environment and quota-related constants for Lambda runtime."""

from __future__ import annotations

import os

# commentThreads.list maxResults ceiling per YouTube API.
MAX_COMMENTS_CAP = 100
# channels.list accepts up to 50 ids per request — used when enriching commenters.
CHANNELS_BATCH_SIZE = 50
DEFAULT_REQUEST_DELAY_MS = 150


def load_api_key() -> str:
    """Load the YouTube API key from environment variables."""
    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()

    if not api_key:
        raise ValueError("No YouTube API key found. Set YOUTUBE_API_KEY in Lambda environment variables.")
    return api_key


def get_request_delay_ms() -> int:
    raw = os.getenv("YOUTUBE_REQUEST_DELAY_MS", "")
    if raw.strip().isdigit():
        return int(raw.strip())
    return DEFAULT_REQUEST_DELAY_MS
