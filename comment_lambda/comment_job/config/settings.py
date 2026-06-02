"""Environment loading for the comment staging Lambda."""

from __future__ import annotations

from comment_job.config.env import _int_env, _optional, _prefix, _required
from comment_job.model import Settings


DEFAULT_COMMENT_STAGE_PREFIX = "staging/comments"
DEFAULT_STAGING_TTL_DAYS = 2
DEFAULT_MAX_COMMENTS = 2000
DEFAULT_REQUEST_DELAY_MS = 150
DEFAULT_MONGO_DB_NAME = "youtube_bot_analytics"
DEFAULT_VIDEOS_COLLECTION = "videos"
DEFAULT_COMMENTS_COLLECTION = "comments"


def load_settings() -> Settings:
    """Load and validate all comment-stage settings from environment variables.

    Returns:
        Frozen Settings model for the current Lambda invocation.
    """
    return Settings(
        youtube_api_key=_required("YOUTUBE_API_KEY"),
        pipeline_s3_bucket=_required("PIPELINE_S3_BUCKET"),
        comment_stage_prefix=_prefix("COMMENT_STAGE_PREFIX", DEFAULT_COMMENT_STAGE_PREFIX),
        staging_ttl_days=_int_env("STAGING_TTL_DAYS", DEFAULT_STAGING_TTL_DAYS, minimum=1),
        max_comments=_int_env("YOUTUBE_MAX_COMMENTS", DEFAULT_MAX_COMMENTS, minimum=1),
        request_delay_ms=_int_env("YOUTUBE_REQUEST_DELAY_MS", DEFAULT_REQUEST_DELAY_MS, minimum=0),
        mongo_uri=_required("MONGO_URI"),
        mongo_db_name=_optional("MONGO_DB_NAME", DEFAULT_MONGO_DB_NAME),
        mongo_videos_collection=_optional("MONGO_VIDEOS_COLLECTION", DEFAULT_VIDEOS_COLLECTION),
        mongo_comments_collection=_optional("MONGO_COMMENTS_COLLECTION", DEFAULT_COMMENTS_COLLECTION),
    )
