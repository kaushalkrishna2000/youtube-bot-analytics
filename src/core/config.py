"""Runtime configuration helpers for the Lambda fetch job.

This module keeps environment-variable parsing and small YouTube API limit
constants in one place. Callers receive normalized Python values or clear
``ValueError`` messages, so the Lambda handler and runner can report config
problems without duplicating parsing logic.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from utils.basic_utils import normalize_nonempty_str_list

## YouTube related ENV
MAX_COMMENTS_CAP = 100  # commentThreads.list maxResults ceiling per YouTube API.
CHANNELS_BATCH_SIZE = 50 # channels.list accepts up to 50 ids per request — used when enriching commenters.
DEFAULT_REQUEST_DELAY_MS = 150
DEFAULT_VIDEO_WORKERS = 1


## AWS related ENV
DEFAULT_FETCH_OUTPUT_S3_PREFIX = "fetch_runs"


def load_api_key() -> str:
    """Return the configured YouTube Data API key.

    Raises:
        ValueError: When ``YOUTUBE_API_KEY`` is missing or blank.
    """
    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()

    if not api_key:
        raise ValueError("No YouTube API key found. Set YOUTUBE_API_KEY in Lambda environment variables.")
    return api_key


def get_request_delay_ms() -> int:
    """Return the inter-request delay in milliseconds.

    Invalid, negative, or missing values fall back to the conservative default.
    The delay is applied by ``YouTubeClient.call`` after each API request.
    """
    raw = os.getenv("YOUTUBE_REQUEST_DELAY_MS", "")
    if raw.strip().isdigit():
        return int(raw.strip())
    return DEFAULT_REQUEST_DELAY_MS


def get_video_workers() -> int:
    """Return the configured per-channel video worker count.

    A value below ``1`` is treated as ``1`` because the report builder always
    needs at least one execution path for video processing.
    """
    raw = os.getenv("YOUTUBE_VIDEO_WORKERS", "")
    if raw.strip().isdigit():
        return max(int(raw.strip()), 1)
    return DEFAULT_VIDEO_WORKERS


def get_s3_output_config(env: Mapping[str, str] | None = None) -> tuple[str, str]:
    """Load and normalize the S3 destination for persisted fetch output.

    Args:
        env: Optional mapping for tests or local callers. When omitted,
            ``os.environ`` is used.

    Returns:
        ``(bucket, prefix)`` where ``prefix`` has no leading/trailing slash and
        never ends up blank.

    Raises:
        ValueError: When the required bucket variable is missing or blank.
    """
    source = os.environ if env is None else env
    bucket = source.get("FETCH_OUTPUT_S3_BUCKET", "").strip()

    if not bucket:
        raise ValueError("No S3 output bucket found. Set FETCH_OUTPUT_S3_BUCKET in Lambda environment variables.")

    raw_prefix = source.get("FETCH_OUTPUT_S3_PREFIX", DEFAULT_FETCH_OUTPUT_S3_PREFIX).strip()
    prefix = raw_prefix.strip("/") or DEFAULT_FETCH_OUTPUT_S3_PREFIX
    return bucket, prefix


def get_configured_channels() -> list[str]:
    """Return the list of channels to process from environment variables.

    Prioritizes YOUTUBE_CHANNELS as a comma-separated list of handles, URLs, or IDs.
    """
    raw_env = os.getenv("YOUTUBE_CHANNELS", "")
    if not raw_env.strip():
        return []
    return normalize_nonempty_str_list(raw_env.split(","))
