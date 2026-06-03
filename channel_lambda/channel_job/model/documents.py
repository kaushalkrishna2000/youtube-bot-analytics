# Mongo document models for channel_lambda
from __future__ import annotations

# Import Pydantic base model and configuration
from pydantic import BaseModel, ConfigDict

# Mongo-ready channel metadata fetched from YouTube
class ChannelDocument(BaseModel):

    # Forbid extra fields to ensure data integrity
    model_config = ConfigDict(extra="forbid")

    # Canonical YouTube channel ID
    channel_id: str

    # Original input string used to resolve the channel
    input_raw: str

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
