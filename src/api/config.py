"""
Environment and quota-related constants.

Loads src/credentials/.env once at import time. Paths are relative to this file
so the app works regardless of the shell's current working directory.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_API_DIR = Path(__file__).resolve().parent
_SRC_ROOT = _API_DIR.parent
_CREDENTIALS_DIR = _SRC_ROOT / "credentials"
_ENV_FILE = _CREDENTIALS_DIR / ".env"

load_dotenv(_ENV_FILE)

# commentThreads.list maxResults ceiling per YouTube API.
MAX_COMMENTS_CAP = 100
# channels.list accepts up to 50 ids per request — used when enriching commenters.
CHANNELS_BATCH_SIZE = 50
DEFAULT_REQUEST_DELAY_MS = 150


def load_api_key() -> str:
    """Load the YouTube API key from the single supported environment source."""
    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()

    if not api_key:
        raise ValueError(
            "No YouTube API key found. Set YOUTUBE_API_KEY in src/credentials/.env "
            "(see src/credentials/.env.example)."
        )
    return api_key


def get_request_delay_ms() -> int:
    raw = os.getenv("YOUTUBE_REQUEST_DELAY_MS", "")
    if raw.strip().isdigit():
        return int(raw.strip())
    return DEFAULT_REQUEST_DELAY_MS
