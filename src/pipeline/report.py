"""
Single-channel pipeline: metadata → optional comments → enrichment.

This is the main hook for extending behavior (extra videos, scoring, etc.).
Catches ChannelNotFoundError and CommentsDisabledError without aborting batch runs.
"""

from __future__ import annotations

import logging

from api import YouTubeClient
from api.config import MAX_COMMENTS_CAP
from models import ChannelNotFoundError, ChannelReport, CommentsDisabledError
from services import enrich_commenter_channels, fetch_top_level_comments, get_channel_report

logger = logging.getLogger(__name__)


def build_full_report(client: YouTubeClient,channel_input: str,*,include_comments: bool = True,max_comments: int = 100,delay_ms: int = 0,) -> ChannelReport:
    """Build channel report with optional comment analysis on latest video."""
    logger.info("Building report for %s", channel_input)
    try:
        report = get_channel_report(client, channel_input, delay_ms=delay_ms)
    except ChannelNotFoundError as exc:
        # Return a minimal report so batch mode can continue and record the failure.
        logger.warning("Channel not found: %s — %s", channel_input, exc)
        return ChannelReport(input_raw=channel_input, error=str(exc))

    if not include_comments:
        logger.info("Comments skipped (--no-comments)")
        report.comments_status = "skipped"
        return report

    if not report.latest_video_id:
        logger.info("No latest video; skipping comments")
        report.comments_status = "no_video"
        return report

    if report.error:
        logger.warning("Channel report has error; skipping comments: %s", report.error)
        return report

    limit = min(max(max_comments, 1), MAX_COMMENTS_CAP)
    logger.info("Fetching comments for video %s (max %s)", report.latest_video_id, limit)

    try:
        comments = fetch_top_level_comments(client, report.latest_video_id, max_comments=limit, delay_ms=delay_ms)
        comments = enrich_commenter_channels(client, comments, delay_ms=delay_ms)
        report.comments = comments
        report.comments_fetched = len(comments)
        report.comments_status = "ok" if comments else "none"
    except CommentsDisabledError:
        # Channel/video metadata is still valid; only the comment phase failed.
        logger.warning("Comments disabled for video %s", report.latest_video_id)
        report.comments = []
        report.comments_fetched = 0
        report.comments_status = "disabled"

    logger.info("Report complete for %s: %s comments (status=%s)", channel_input, report.comments_fetched, report.comments_status)
    return report
