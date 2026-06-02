"""Domain dataclasses for YouTube channel batch fetch results.

The service and logic layers build these records in memory, then the runner
serializes them into the S3 JSON payload. The shapes are intentionally simple:
one ``ChannelReport`` per requested input, one ``VideoReport`` per fetched
upload, and one ``CommentRecord`` per top-level comment.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

EnrichmentStatus = Literal["ok", "no_channel", "not_found", "pending"]
"""Comment author channel enrichment outcome.

``pending`` is used before enrichment runs, ``ok`` means author metadata was
found, ``no_channel`` means YouTube did not provide an author channel ID, and
``not_found`` means the author channel ID was not returned by ``channels.list``.
"""

CommentsStatus = Literal["ok", "disabled", "none", "skipped", "partial", "error"]
"""Video-level comment fetch outcome stored on ``VideoReport``."""


@dataclass
class CommentRecord:
    """One top-level comment plus optional enriched author channel fields.

    The initial comment fetch populates comment text, publish time, likes, and
    author ID. ``services.youtube.comment.enrich_commenter_channels`` later fills the
    author channel fields when YouTube returns matching channel metadata.
    """

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
        """Return a JSON-safe dictionary representation."""
        return asdict(self)


@dataclass(frozen=True)
class VideoSummary:
    """Minimal video metadata used before and after comment fetching."""

    video_id: str
    title: str
    published_at: str


@dataclass
class VideoReport:
    """One video result with comments and a fetch-status flag.

    ``comments_status`` summarizes the outcome even when the comment list is
    empty, so downstream consumers can distinguish no comments, skipped comment
    fetches, disabled comments, and errors.
    """

    video: VideoSummary
    comments: list[CommentRecord] = field(default_factory=list)
    comments_fetched: int = 0
    comments_status: CommentsStatus = "none"
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return the nested JSON-safe shape used in runner payloads."""
        return {
            "video": asdict(self.video),
            "comments_fetched": self.comments_fetched,
            "comments_status": self.comments_status,
            "comments": [c.to_dict() for c in self.comments],
            "error": self.error,
        }


@dataclass
class ChannelReport:
    """Aggregated result for one requested channel input.

    A report may contain only ``input_raw`` and ``error`` when the channel could
    not be resolved or fetched. Successful reports include channel metadata and
    zero or more ``VideoReport`` entries.
    """

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
        """Return the nested JSON-safe shape persisted to S3."""
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
