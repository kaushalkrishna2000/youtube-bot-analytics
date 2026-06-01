"""Environment and quota-related constants for Lambda runtime."""

from __future__ import annotations

import os
from collections.abc import Mapping

# commentThreads.list maxResults ceiling per YouTube API.
MAX_COMMENTS_CAP = 100
# channels.list accepts up to 50 ids per request — used when enriching commenters.
CHANNELS_BATCH_SIZE = 50
DEFAULT_REQUEST_DELAY_MS = 150
DEFAULT_FETCH_OUTPUT_S3_PREFIX = "fetch_runs"
FETCH_OUTPUT_S3_BUCKET_ENV = "FETCH_OUTPUT_S3_BUCKET"
FETCH_OUTPUT_S3_PREFIX_ENV = "FETCH_OUTPUT_S3_PREFIX"


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


def get_s3_output_config(env: Mapping[str, str] | None = None) -> tuple[str, str]:
    """Load and normalize the S3 destination from Lambda environment variables."""
    source = os.environ if env is None else env
    bucket = source.get(FETCH_OUTPUT_S3_BUCKET_ENV, "").strip()

    if not bucket:
        raise ValueError(f"No S3 output bucket found. Set {FETCH_OUTPUT_S3_BUCKET_ENV} in Lambda environment variables.")

    raw_prefix = source.get(FETCH_OUTPUT_S3_PREFIX_ENV, DEFAULT_FETCH_OUTPUT_S3_PREFIX).strip()
    prefix = raw_prefix.strip("/") or DEFAULT_FETCH_OUTPUT_S3_PREFIX
    return bucket, prefix
