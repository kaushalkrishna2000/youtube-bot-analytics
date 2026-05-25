"""
Domain dataclasses for one channel run.

ChannelReport is the unit exported to JSON/CSV. CommentRecord starts with
enrichment_status='pending' or 'no_channel' and is updated in comment_service.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

# Per-comment: whether we loaded the commenter's channel snippet.
EnrichmentStatus = Literal["ok", "no_channel", "not_found", "pending"]
# Per-report: outcome of the comment-fetch phase for the latest video.
CommentsStatus = Literal["ok", "disabled", "none", "skipped", "no_video"]


@dataclass(frozen=True)
class VideoSummary:
    """Latest upload on the target channel (from uploads playlist, maxResults=1)."""

    video_id: str
    title: str
    published_at: str


@dataclass
class CommentRecord:
    """One top-level comment plus optional enriched author channel fields."""

    comment_id: str
    comment_text: str
    comment_published_at: str
    author_display_name: str
    author_channel_id: str | None
    like_count: int
    author_channel_title: str | None = None
    author_channel_created_at: str | None = None
    author_channel_custom_url: str | None = None
    enrichment_status: EnrichmentStatus = "pending"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ChannelReport:
    """Aggregated result for a single channel input (success or partial failure)."""

    input_raw: str
    channel_id: str | None = None
    title: str | None = None
    custom_url: str | None = None
    channel_created_at: str | None = None
    subscriber_count: int | None = None
    video_count: int | None = None
    latest_video: VideoSummary | None = None
    comments: list[CommentRecord] = field(default_factory=list)
    comments_fetched: int = 0
    comments_status: CommentsStatus = "none"
    error: str | None = None

    @property
    def latest_video_id(self) -> str | None:
        return self.latest_video.video_id if self.latest_video else None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "input_raw": self.input_raw,
            "channel_id": self.channel_id,
            "title": self.title,
            "custom_url": self.custom_url,
            "channel_created_at": self.channel_created_at,
            "subscriber_count": self.subscriber_count,
            "video_count": self.video_count,
            "latest_video": asdict(self.latest_video) if self.latest_video else None,
            "comments_fetched": self.comments_fetched,
            "comments_status": self.comments_status,
            "comments": [c.to_dict() for c in self.comments],
            "error": self.error,
        }
        return data
