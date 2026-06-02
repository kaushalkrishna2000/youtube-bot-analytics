"""Environment loading for the channel staging Lambda."""

from __future__ import annotations

from channel_job.config.env import _int_env, _optional, _prefix, _required
from channel_job.model import Settings


DEFAULT_CHANNEL_STAGE_PREFIX = "staging/channels"
DEFAULT_STAGING_TTL_DAYS = 2
DEFAULT_REQUEST_DELAY_MS = 150
DEFAULT_MONGO_DB_NAME = "youtube_bot_analytics"
DEFAULT_CHANNELS_COLLECTION = "channels"

# Optional code-based channel source. Leave empty to use YOUTUBE_CHANNELS.
# Entries can be @handles, UC... channel IDs, names, or YouTube channel URLs.
CODE_CHANNELS: list[str] = []


def load_settings() -> Settings:
    """Load and validate all channel-stage settings from environment variables.

    Returns:
        Frozen Settings model for the current Lambda invocation.
    """
    return Settings(
        youtube_api_key=_required("YOUTUBE_API_KEY"),
        youtube_channels=_load_channel_inputs(),
        pipeline_s3_bucket=_required("PIPELINE_S3_BUCKET"),
        channel_stage_prefix=_prefix("CHANNEL_STAGE_PREFIX", DEFAULT_CHANNEL_STAGE_PREFIX),
        staging_ttl_days=_int_env("STAGING_TTL_DAYS", DEFAULT_STAGING_TTL_DAYS, minimum=1),
        request_delay_ms=_int_env("YOUTUBE_REQUEST_DELAY_MS", DEFAULT_REQUEST_DELAY_MS, minimum=0),
        mongo_uri=_required("MONGO_URI"),
        mongo_db_name=_optional("MONGO_DB_NAME", DEFAULT_MONGO_DB_NAME),
        mongo_channels_collection=_optional("MONGO_CHANNELS_COLLECTION", DEFAULT_CHANNELS_COLLECTION),
    )


def _load_channel_inputs() -> list[str]:
    """Load channel inputs from environment first, then code defaults.

    Returns:
        Non-empty channel identifiers from ``YOUTUBE_CHANNELS`` or
        ``CODE_CHANNELS``.
    """
    import os

    raw_channels = os.getenv("YOUTUBE_CHANNELS", "").strip()
    if raw_channels:
        return [item.strip() for item in raw_channels.split(",") if item.strip()]
    return [item.strip() for item in CODE_CHANNELS if isinstance(item, str) and item.strip()]
