# Mongo document models for video_lambda
from __future__ import annotations

# Import Pydantic base model and configuration
from pydantic import BaseModel, ConfigDict

# Channel metadata copied from the upstream channel-stage payload
class ChannelDocument(BaseModel):

    # Ignore extra fields to maintain compatibility with upstream changes
    model_config = ConfigDict(extra="ignore")

    # Canonical YouTube channel ID
    channel_id: str

    # Original input string used to resolve the channel
    input_raw: str | None = None

    # Display title of the channel
    title: str | None = None

    # Custom URL handle if available
    custom_url: str | None = None

    # ISO 8601 timestamp of channel creation
    channel_created_at: str | None = None

    # Current number of subscribers
    subscriber_count: int | None = None

    # Total number of videos uploaded
    video_count: int | None = None

# Mongo-ready video metadata fetched from a channel uploads playlist
class VideoDocument(BaseModel):

    # Forbid extra fields to ensure data integrity
    model_config = ConfigDict(extra="forbid")

    # Canonical YouTube video ID
    video_id: str

    # ID of the channel that owns this video
    channel_id: str

    # Display title of the video
    title: str | None = None

    # ISO 8601 timestamp of video publication
    published_at: str | None = None

    # Current status of comment fetching for this video
    comments_status: str = "pending"

    # Number of comments successfully fetched
    comments_fetched: int = 0

    # Error message if comment fetching failed
    comments_error: str | None = None
