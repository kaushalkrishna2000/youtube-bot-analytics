"""Mongo document models for channel_lambda."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ChannelDocument(BaseModel):
    """Mongo-ready channel metadata fetched from YouTube."""

    model_config = ConfigDict(extra="forbid")

    channel_id: str
    input_raw: str
    title: str | None = None
    custom_url: str | None = None
    channel_created_at: str | None = None
    subscriber_count: int | None = None
    video_count: int | None = None
