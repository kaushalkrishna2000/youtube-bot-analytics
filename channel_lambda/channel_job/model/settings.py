"""Settings model for channel_lambda."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    youtube_api_key: str
    youtube_channels: list[str]
    pipeline_s3_bucket: str
    channel_stage_prefix: str
    staging_ttl_days: int
    request_delay_ms: int
    mongo_uri: str
    mongo_db_name: str
    mongo_channels_collection: str
    mongo_videos_collection: str
    mongo_comments_collection: str
