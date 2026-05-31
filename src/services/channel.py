"""Load target channel metadata and latest uploads with pagination."""

from __future__ import annotations

import logging

from api.client import YouTubeClient
from models.records import ChannelReport, VideoSummary
from utils.resolver import resolve_channel_id

logger = logging.getLogger(__name__)
_VIDEO_BATCH_SIZE = 50


def get_channel_report(client: YouTubeClient, channel_input: str, *, delay_ms: int = 0) -> ChannelReport:
    """Resolve channel and return channel metadata only (no comments)."""
    report = ChannelReport(input_raw=channel_input)

    channel_id = resolve_channel_id(client, channel_input)
    report.channel_id = channel_id

    logger.info("Fetching channel metadata for %s", channel_id)
    channel_request = client.service.channels().list(part="snippet,statistics,contentDetails", id=channel_id)
    channel_response = client.call(channel_request, delay_ms=delay_ms)
    items = channel_response.get("items", [])
    if not items:
        report.error = f"Channel not found: {channel_id}"
        return report

    channel = items[0]
    snippet = channel.get("snippet", {})
    statistics = channel.get("statistics", {})

    report.title = snippet.get("title")
    report.custom_url = snippet.get("customUrl")
    report.channel_created_at = snippet.get("publishedAt")
    report.subscriber_count = _parse_int(statistics.get("subscriberCount"))
    report.video_count = _parse_int(statistics.get("videoCount"))
    return report


def fetch_latest_videos(client: YouTubeClient, channel_id: str, *, max_videos: int = 10, delay_ms: int = 0) -> list[VideoSummary]:
    """Fetch latest N uploaded videos for a channel using uploads-playlist pagination."""
    if max_videos <= 0:
        return []
    logger.info("Fetching latest %s video(s) for channel %s", max_videos, channel_id)

    channel_request = client.service.channels().list(part="contentDetails", id=channel_id)
    channel_response = client.call(channel_request, delay_ms=delay_ms)
    items = channel_response.get("items", [])
    if not items:
        return []

    uploads_playlist_id = items[0].get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
    if not uploads_playlist_id:
        logger.info("No uploads playlist found for channel %s", channel_id)
        return []

    video_ids: list[str] = []
    next_page_token: str | None = None

    while len(video_ids) < max_videos:
        page_size = min(50, max_videos - len(video_ids))
        playlist_request = client.service.playlistItems().list(
            part="contentDetails",
            playlistId=uploads_playlist_id,
            maxResults=page_size,
            pageToken=next_page_token,
        )
        playlist_response = client.call(playlist_request, delay_ms=delay_ms)
        page_items = playlist_response.get("items", [])
        logger.info("Fetched uploads page: %s video id(s) (total=%s/%s)", len(page_items), len(video_ids), max_videos)
        for item in page_items:
            video_id = item.get("contentDetails", {}).get("videoId")
            if video_id:
                video_ids.append(video_id)
                if len(video_ids) >= max_videos:
                    break

        next_page_token = playlist_response.get("nextPageToken")
        if not next_page_token or not page_items:
            break

    if not video_ids:
        logger.info("No uploaded videos found for channel %s", channel_id)
        return []

    summaries: list[VideoSummary] = []
    for start in range(0, len(video_ids), _VIDEO_BATCH_SIZE):
        batch_ids = video_ids[start : start + _VIDEO_BATCH_SIZE]
        logger.info("Hydrating video metadata batch: %s video(s)", len(batch_ids))
        request = client.service.videos().list(part="snippet", id=",".join(batch_ids))
        response = client.call(request, delay_ms=delay_ms)

        snippet_map: dict[str, dict] = {}
        for video in response.get("items", []):
            vid = video.get("id")
            if vid:
                snippet_map[vid] = video.get("snippet", {})

        for vid in batch_ids:
            snippet = snippet_map.get(vid, {})
            summaries.append(
                VideoSummary(
                    video_id=vid,
                    title=snippet.get("title", ""),
                    published_at=snippet.get("publishedAt", ""),
                )
            )

    logger.info("Resolved %s latest video(s) for channel %s", len(summaries), channel_id)
    return summaries


def _parse_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None
