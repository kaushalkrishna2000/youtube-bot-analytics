"""
Load target channel metadata and identify its newest upload.

Uses channels.list → uploads playlist → playlistItems (1 item) → videos.list.
Does not fetch comments; see comment_service and pipeline.report.
"""

from __future__ import annotations

import logging

from api import YouTubeClient
from models import ChannelReport, VideoSummary
from utils.resolver import resolve_channel_id

logger = logging.getLogger(__name__)


def _parse_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def get_channel_report(client: YouTubeClient, channel_input: str, *, delay_ms: int = 0) -> ChannelReport:
    """Resolve channel and return metadata plus the latest video summary."""
    report = ChannelReport(input_raw=channel_input)

    channel_id = resolve_channel_id(client, channel_input)
    report.channel_id = channel_id

    # snippet + statistics + contentDetails (uploads playlist id lives in contentDetails).
    logger.info("Fetching channel metadata for %s", channel_id)
    channel_request = client.service.channels().list(part="snippet,statistics,contentDetails",id=channel_id)
    channel_response = client.call(channel_request, delay_ms=delay_ms)
    items = channel_response.get("items", [])
    logger.debug("channels.list returned %s item(s)", len(items))
    if not items:
        report.error = f"Channel not found: {channel_id}"
        logger.warning("Channel not found after resolve: %s", channel_id)
        return report

    channel = items[0]
    snippet = channel.get("snippet", {})
    statistics = channel.get("statistics", {})
    content_details = channel.get("contentDetails", {})

    report.title = snippet.get("title")
    report.custom_url = snippet.get("customUrl")
    report.channel_created_at = snippet.get("publishedAt")
    report.subscriber_count = _parse_int(statistics.get("subscriberCount"))
    report.video_count = _parse_int(statistics.get("videoCount"))

    # Every channel has an implicit "uploads" playlist; first item = most recent video.
    uploads_playlist_id = content_details.get("relatedPlaylists", {}).get("uploads")
    if not uploads_playlist_id:
        logger.info("No uploads playlist for channel %s", channel_id)
        return report

    logger.info("Fetching latest video from uploads playlist")
    playlist_request = client.service.playlistItems().list(part="contentDetails",playlistId=uploads_playlist_id,maxResults=1)
    playlist_response = client.call(playlist_request, delay_ms=delay_ms)
    playlist_items = playlist_response.get("items", [])
    logger.debug("playlistItems.list returned %s item(s)", len(playlist_items))
    if not playlist_items:
        logger.info("No videos in uploads playlist")
        return report

    video_id = playlist_items[0]["contentDetails"]["videoId"]
    video_request = client.service.videos().list(part="snippet", id=video_id)
    video_response = client.call(video_request, delay_ms=delay_ms)
    video_items = video_response.get("items", [])
    logger.debug("videos.list returned %s item(s)", len(video_items))
    if not video_items:
        logger.info("Latest video %s not found via API", video_id)
        return report

    video_snippet = video_items[0].get("snippet", {})
    report.latest_video = VideoSummary(video_id=video_id, title=video_snippet.get("title", ""), published_at=video_snippet.get("publishedAt", ""))
    logger.info("Latest video: %s — %s", video_id, report.latest_video.title)
    return report
