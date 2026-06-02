"""Stage payload models for channel_lambda."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from channel_job.model.documents import ChannelDocument


class ChannelStagePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    stage: Literal["channel"]
    job_id: str
    created_at: str
    expires_at: str
    channel: ChannelDocument


class UploadMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bucket: str
    key: str
    s3_uri: str
    size_bytes: int
    etag: str | None = None
