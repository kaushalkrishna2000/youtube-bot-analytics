"""Mongo document models for video_lambda."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ChannelDocument(BaseModel):
    model_config = ConfigDict(extra="ignore")

    channel_id: str
    input_raw: str | None = None
    title: str | None = None
    custom_url: str | None = None
    channel_created_at: str | None = None
    subscriber_count: int | None = None
    video_count: int | None = None


class VideoDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    video_id: str
    channel_id: str
    title: str | None = None
    published_at: str | None = None
    comments_status: str = "pending"
    comments_fetched: int = 0
    comments_error: str | None = None
