"""Environment loading for the video staging Lambda."""

from __future__ import annotations

from video_job.config.env import _int_env, _optional, _prefix, _required
from video_job.model import Settings


DEFAULT_VIDEO_STAGE_PREFIX = "staging/videos"
DEFAULT_STAGING_TTL_DAYS = 2
DEFAULT_MAX_VIDEOS = 20
DEFAULT_REQUEST_DELAY_MS = 150
DEFAULT_MONGO_DB_NAME = "youtube_bot_analytics"
DEFAULT_CHANNELS_COLLECTION = "channels"
DEFAULT_VIDEOS_COLLECTION = "videos"
DEFAULT_COMMENTS_COLLECTION = "comments"


def load_settings() -> Settings:
    return Settings(
        youtube_api_key=_required("YOUTUBE_API_KEY"),
        pipeline_s3_bucket=_required("PIPELINE_S3_BUCKET"),
        video_stage_prefix=_prefix("VIDEO_STAGE_PREFIX", DEFAULT_VIDEO_STAGE_PREFIX),
        staging_ttl_days=_int_env("STAGING_TTL_DAYS", DEFAULT_STAGING_TTL_DAYS, minimum=1),
        max_videos=_int_env("YOUTUBE_MAX_VIDEOS", DEFAULT_MAX_VIDEOS, minimum=1),
        request_delay_ms=_int_env("YOUTUBE_REQUEST_DELAY_MS", DEFAULT_REQUEST_DELAY_MS, minimum=0),
        mongo_uri=_required("MONGO_URI"),
        mongo_db_name=_optional("MONGO_DB_NAME", DEFAULT_MONGO_DB_NAME),
        mongo_channels_collection=_optional("MONGO_CHANNELS_COLLECTION", DEFAULT_CHANNELS_COLLECTION),
        mongo_videos_collection=_optional("MONGO_VIDEOS_COLLECTION", DEFAULT_VIDEOS_COLLECTION),
        mongo_comments_collection=_optional("MONGO_COMMENTS_COLLECTION", DEFAULT_COMMENTS_COLLECTION),
    )

