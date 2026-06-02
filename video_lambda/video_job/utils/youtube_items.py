"""YouTube API item parsing helpers for video_lambda."""

from __future__ import annotations

from typing import Any


def extract_video_id(item: dict[str, Any]) -> str | None:
    video_id = item.get("contentDetails", {}).get("videoId")
    return video_id if isinstance(video_id, str) and video_id else None
