"""Mongo document models for comment_lambda."""

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
    model_config = ConfigDict(extra="ignore")

    video_id: str
    channel_id: str
    title: str | None = None
    published_at: str | None = None
    comments_status: str = "pending"
    comments_fetched: int = 0
    comments_error: str | None = None


class CommentDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    comment_id: str
    channel_id: str
    video_id: str
    comment_text: str | None = None
    comment_published_at: str | None = None
    author_display_name: str | None = None
    author_channel_id: str | None = None
    like_count: int = 0
    author_channel_title: str | None = None
    author_channel_created_at: str | None = None
    author_channel_custom_url: str | None = None
    enrichment_status: str = "pending"
