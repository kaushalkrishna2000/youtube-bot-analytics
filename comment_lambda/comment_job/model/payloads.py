# Stage payload models for comment_lambda
from __future__ import annotations

# Import literal typing utility
from typing import Literal

# Import Pydantic base model and configuration
from pydantic import BaseModel, ConfigDict

# Import the local channel, comment, and video document models
from comment_job.model.documents import ChannelDocument, CommentDocument, VideoDocument

# Upstream S3 payload read from the video staging prefix
class VideoStagePayload(BaseModel):

    # Ignore extra fields to maintain compatibility with future upstream changes
    model_config = ConfigDict(extra="ignore")

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

    # Associated video metadata
    video: VideoDocument

# Durable S3 payload containing the comment fetch result for one video
class CommentStagePayload(BaseModel):

    # Forbid extra fields to ensure data integrity
    model_config = ConfigDict(extra="forbid")

    # Version identifier for the payload schema
    schema_version: str

    # Constant stage identifier
    stage: Literal["comment"]

    # Unique job identifier for tracing
    job_id: str

    # ISO 8601 timestamp of payload creation
    created_at: str

    # ISO 8601 timestamp of payload expiration
    expires_at: str

    # Associated channel metadata
    channel: ChannelDocument

    # Associated video metadata
    video: VideoDocument

    # Status of the comment fetching process
    comments_status: str

    # Number of comments fetched in this payload
    comments_fetched: int

    # List of resolved comment documents
    comments: list[CommentDocument]

    # Error message if the fetch failed
    error: str | None = None

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
