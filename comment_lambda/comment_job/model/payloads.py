"""Stage payload models for comment_lambda."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from comment_job.model.documents import ChannelDocument, CommentDocument, VideoDocument


class VideoStagePayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    schema_version: str
    stage: Literal["video"]
    job_id: str
    created_at: str
    expires_at: str
    channel: ChannelDocument
    video: VideoDocument


class CommentStagePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    stage: Literal["comment"]
    job_id: str
    created_at: str
    expires_at: str
    channel: ChannelDocument
    video: VideoDocument
    comments_status: str
    comments_fetched: int
    comments: list[CommentDocument]
    error: str | None = None


class UploadMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bucket: str
    key: str
    s3_uri: str
    size_bytes: int
    etag: str | None = None
