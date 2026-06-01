"""
Domain dataclasses for channel batch fetch runs.

Channel-mode reports are multi-video.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

EnrichmentStatus = Literal["ok", "no_channel", "not_found", "pending"]
CommentsStatus = Literal["ok", "disabled", "none", "skipped", "partial", "error"]


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


@dataclass(frozen=True)
class VideoSummary:
    """Video metadata used in channel batch reports."""

    video_id: str
    title: str
    published_at: str


@dataclass
class VideoReport:
    """One video analysis result with comment fetch outcome."""

    video: VideoSummary
    comments: list[CommentRecord] = field(default_factory=list)
    comments_fetched: int = 0
    comments_status: CommentsStatus = "none"
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "video": asdict(self.video),
            "comments_fetched": self.comments_fetched,
            "comments_status": self.comments_status,
            "comments": [c.to_dict() for c in self.comments],
            "error": self.error,
        }


@dataclass
class ChannelReport:
    """Aggregated result for one channel input (single or batch item)."""

    input_raw: str
    channel_id: str | None = None
    title: str | None = None
    custom_url: str | None = None
    channel_created_at: str | None = None
    subscriber_count: int | None = None
    video_count: int | None = None
    videos: list[VideoReport] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_raw": self.input_raw,
            "channel_id": self.channel_id,
            "title": self.title,
            "custom_url": self.custom_url,
            "channel_created_at": self.channel_created_at,
            "subscriber_count": self.subscriber_count,
            "video_count": self.video_count,
            "videos": [v.to_dict() for v in self.videos],
            "error": self.error,
        }
