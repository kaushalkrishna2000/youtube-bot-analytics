# Mongo document models for comment_lambda
from __future__ import annotations

# Import Pydantic base model and configuration
from pydantic import BaseModel, ConfigDict

# Channel metadata copied from an upstream stage payload
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

# Video metadata copied from the upstream video-stage payload
class VideoDocument(BaseModel):

    # Ignore extra fields to maintain compatibility with upstream changes
    model_config = ConfigDict(extra="ignore")

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

# Mongo-ready top-level comment with optional author-channel enrichment
class CommentDocument(BaseModel):

    # Forbid extra fields to ensure data integrity
    model_config = ConfigDict(extra="forbid")

    # Canonical YouTube comment ID
    comment_id: str

    # ID of the channel that owns the video
    channel_id: str

    # ID of the video the comment belongs to
    video_id: str

    # Raw text content of the comment
    comment_text: str | None = None

    # ISO 8601 timestamp of comment publication
    comment_published_at: str | None = None

    # Display name of the comment author
    author_display_name: str | None = None

    # YouTube channel ID of the comment author
    author_channel_id: str | None = None

    # Number of likes the comment has received
    like_count: int = 0

    # Display title of the author's channel
    author_channel_title: str | None = None

    # ISO 8601 timestamp of the author's channel creation
    author_channel_created_at: str | None = None

    # Custom URL handle of the author's channel
    author_channel_custom_url: str | None = None

    # Current status of additional author metadata enrichment
    enrichment_status: str = "pending"
