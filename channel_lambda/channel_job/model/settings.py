# Settings model for channel_lambda
from __future__ import annotations

# Import Pydantic base model and configuration
from pydantic import BaseModel, ConfigDict

# Validated environment settings for the channel staging Lambda
class Settings(BaseModel):

    # Forbid extra fields and mark the object as immutable
    model_config = ConfigDict(extra="forbid", frozen=True)

    # YouTube Data API key
    youtube_api_key: str

    # List of channel IDs or handles to monitor
    youtube_channels: list[str]

    # Destination S3 bucket for staging payloads
    pipeline_s3_bucket: str

    # Key prefix for channel stage objects in S3
    channel_stage_prefix: str

    # Number of days before staged data is considered expired
    staging_ttl_days: int

    # Throttling delay between YouTube API requests
    request_delay_ms: int

    # MongoDB connection string
    mongo_uri: str

    # Target MongoDB database name
    mongo_db_name: str

    # Target MongoDB collection for channel documents
    mongo_channels_collection: str
