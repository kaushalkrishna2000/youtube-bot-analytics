"""Stage payload models for video_lambda."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from video_job.model.documents import ChannelDocument, VideoDocument


class ChannelStagePayload(BaseModel):
    """Upstream S3 payload read from the channel staging prefix."""

    model_config = ConfigDict(extra="ignore")

    schema_version: str
    stage: Literal["channel"]
    job_id: str
    created_at: str
    expires_at: str
    channel: ChannelDocument


class VideoStagePayload(BaseModel):
    """Durable S3 payload handed from video stage to comment stage."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str
    stage: Literal["video"]
    job_id: str
    created_at: str
    expires_at: str
    channel: ChannelDocument
    video: VideoDocument


class UploadMetadata(BaseModel):
    """Metadata returned after writing a stage payload to S3."""

    model_config = ConfigDict(extra="forbid")

    bucket: str
    key: str
    s3_uri: str
    size_bytes: int
    etag: str | None = None
