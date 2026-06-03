# Runtime dependency model for video_lambda
from __future__ import annotations

# Import type hinting utilities
from typing import Any

# Import Pydantic base model and configuration
from pydantic import BaseModel, ConfigDict

# Import the local settings model
from video_job.model.settings import Settings

# Per-invocation dependency bundle for the video staging runner
class Runtime(BaseModel):

    # Allow arbitrary types for external clients
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    # Validated application settings
    settings: Settings

    # Raw AWS Lambda event payload
    event: dict[str, Any] | None

    # YouTube API client instance
    youtube_client: Any

    # Boto3 S3 client instance
    s3_client: Any

    # MongoDB persistence writer
    mongo_writer: Any
