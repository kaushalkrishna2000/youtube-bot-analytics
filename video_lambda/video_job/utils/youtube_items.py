"""YouTube API item parsing helpers for video_lambda."""

from __future__ import annotations

from typing import Any


def extract_video_id(item: dict[str, Any]) -> str | None:

    # Extract the video ID from the content details of a playlist item
    video_id = item.get("contentDetails", {}).get("videoId")

    # Return the ID if it is a non-empty string, otherwise return None
    return video_id if isinstance(video_id, str) and video_id else None
