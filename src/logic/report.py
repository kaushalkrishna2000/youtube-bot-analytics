"""Report builders for channel batch fetch mode."""

from __future__ import annotations

import logging

from core.youtube_client import YouTubeClient
from models.exceptions import ChannelNotFoundError, CommentsDisabledError
from models.records import ChannelReport, VideoReport, VideoSummary
from services.channel import fetch_latest_videos, get_channel_report
from services.comment import enrich_commenter_channels, fetch_top_level_comments

logger = logging.getLogger(__name__)


def build_channel_report(client: YouTubeClient, channel_input: str, *, include_comments: bool = True, max_videos: int = 10, max_comments: int = 1000, delay_ms: int = 0) -> ChannelReport:
    """Build channel report with latest N videos and per-video comment analysis."""
    logger.info("Building channel report for %s", channel_input)
    try:
        report = get_channel_report(client, channel_input, delay_ms=delay_ms)
    except ChannelNotFoundError as exc:
        return ChannelReport(input_raw=channel_input, error=str(exc))

    if report.error or not report.channel_id:
        return report

    videos = fetch_latest_videos(client, report.channel_id, max_videos=max_videos, delay_ms=delay_ms)
    if not videos:
        logger.info("No videos found for channel %s", report.channel_id)
        return report

    if not include_comments:
        logger.info("Comments disabled by flag; marking %s video(s) as skipped", len(videos))
        report.videos = [VideoReport(video=v, comments=[], comments_fetched=0, comments_status="skipped") for v in videos]
        return report

    built: list[VideoReport] = []
    for video in videos:
        logger.info("Processing video %s (%s)", video.video_id, video.title)
        built.append(_build_video_report_for_summary(client, video, max_comments=max_comments, delay_ms=delay_ms))

    report.videos = built
    logger.info("Channel report complete for %s: %s video(s)", channel_input, len(built))
    return report


def _build_video_report_for_summary(client: YouTubeClient, video: VideoSummary, *, max_comments: int, delay_ms: int) -> VideoReport:
    try:
        comments, fetch_status = fetch_top_level_comments(client, video.video_id, max_comments=max_comments, delay_ms=delay_ms)
        comments = enrich_commenter_channels(client, comments, delay_ms=delay_ms)
        status = fetch_status if comments else ("none" if fetch_status == "ok" else fetch_status)
        return VideoReport(video=video, comments=comments, comments_fetched=len(comments), comments_status=status)
    except CommentsDisabledError:
        return VideoReport(video=video, comments=[], comments_fetched=0, comments_status="disabled")
    except Exception as exc:
        logger.exception("Video processing failed for %s", video.video_id)
        return VideoReport(video=video, comments=[], comments_fetched=0, comments_status="error", error=str(exc))
