# Stage payload models for video_lambda
from __future__ import annotations

# Import literal typing utility
from typing import Literal

# Import Pydantic base model and configuration
from pydantic import BaseModel, ConfigDict

# Import the local channel and video document models
from video_job.model.documents import ChannelDocument, VideoDocument

# Upstream S3 payload read from the channel staging prefix
class ChannelStagePayload(BaseModel):

    # Ignore extra fields to maintain compatibility with future upstream changes
    model_config = ConfigDict(extra="ignore")

    # Version identifier for the payload schema
    schema_version: str

    # Constant stage identifier
    stage: Literal["channel"]

    # Unique job identifier for tracing
    job_id: str

    # ISO 8601 timestamp of payload creation
    created_at: str

    # ISO 8601 timestamp of payload expiration
    expires_at: str

    # Resolved channel metadata
    channel: ChannelDocument

# Durable S3 payload handed from video stage to comment stage
class VideoStagePayload(BaseModel):

    # Forbid extra fields to ensure data integrity
    model_config = ConfigDict(extra="forbid")

    # Version identifier for the payload schema
    schema_version: str

    # Constant stage identifier
    stage: Literal["video"]

    # Unique job identifier for tracing
    job_id: str

    # ISO 8601 timestamp of payload creation
    created_at: str

    # ISO 8601 timestamp of payload expiration
    expires_at: str

    # Associated channel metadata
    channel: ChannelDocument

    # Resolved video metadata
    video: VideoDocument

# Metadata returned after writing a stage payload to S3
class UploadMetadata(BaseModel):

    # Forbid extra fields to ensure data integrity
    model_config = ConfigDict(extra="forbid")

    # Destination S3 bucket name
    bucket: str

    # Destination S3 key path
    key: str

    # Canonical S3 URI of the uploaded object
    s3_uri: str

    # Size of the uploaded object in bytes
    size_bytes: int

    # ETag value returned by S3
    etag: str | None = None
