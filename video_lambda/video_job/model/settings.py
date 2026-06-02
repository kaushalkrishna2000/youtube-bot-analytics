"""Settings model for video_lambda."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    youtube_api_key: str
    pipeline_s3_bucket: str
    video_stage_prefix: str
    staging_ttl_days: int
    max_videos: int
    request_delay_ms: int
    mongo_uri: str
    mongo_db_name: str
    mongo_videos_collection: str
