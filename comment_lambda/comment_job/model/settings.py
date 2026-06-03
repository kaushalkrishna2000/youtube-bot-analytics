# Settings model for comment_lambda
from __future__ import annotations

# Import Pydantic base model and configuration
from pydantic import BaseModel, ConfigDict

# Validated environment settings for the comment staging Lambda
class Settings(BaseModel):

    # Forbid extra fields and mark the object as immutable
    model_config = ConfigDict(extra="forbid", frozen=True)

    # YouTube Data API key
    youtube_api_key: str

    # Destination S3 bucket for staging payloads
    pipeline_s3_bucket: str

    # Key prefix for comment stage objects in S3
    comment_stage_prefix: str

    # Number of days before staged data is considered expired
    staging_ttl_days: int

    # Maximum number of top-level comments to fetch per video
    max_comments: int

    # Throttling delay between YouTube API requests
    request_delay_ms: int

    # MongoDB connection string
    mongo_uri: str

    # Target MongoDB database name
    mongo_db_name: str

    # Target MongoDB collection for video metadata
    mongo_videos_collection: str

    # Target MongoDB collection for comment documents
    mongo_comments_collection: str
