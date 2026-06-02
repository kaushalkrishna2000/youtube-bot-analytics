"""Consolidated orchestration for YouTube channel and video fetching.

This module provides the main entry points for building reports:
- ``run_batch``: Processes multiple channel inputs.
- ``build_channel_report``: Processes a single channel input.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.youtube_client import YouTubeClient
from core.exceptions import ChannelNotFoundError, CommentsDisabledError
from domain.models import ChannelReport, VideoReport, VideoSummary
from services.youtube.channel import fetch_latest_videos, get_channel_report
from services.youtube.comment import enrich_commenter_channels, fetch_top_level_comments

logger = logging.getLogger(__name__)


def run_batch(client: YouTubeClient,channel_inputs: list[str],*,include_comments: bool = True,
              max_videos: int = 10,max_comments: int = 1000,
              delay_ms: int = 0,video_workers: int = 1) -> tuple[list[ChannelReport], list[tuple[str, str]]]:
    """Build reports for each channel input and collect failures.

    Returns:
        ``(reports, failures)`` where failures are ``(channel_input, error)``
        tuples. A failed channel still receives an error-only ``ChannelReport``
        so the report list mirrors the requested inputs as much as possible.
    """
    reports: list[ChannelReport] = []
    failures: list[tuple[str, str]] = []
    total = len(channel_inputs)
    logger.info("Starting batch run for %s channel(s)", total)

    for index, channel_input in enumerate(channel_inputs, start=1):
        logger.info("Processing [%s/%s]: %s", index, total, channel_input)
        try:
            report = build_channel_report(
                client,
                channel_input,
                include_comments=include_comments,
                max_videos=max_videos,
                max_comments=max_comments,
                delay_ms=delay_ms,
                video_workers=video_workers,
            )
            if report.error:
                # Expected service-level failures are represented on the report
                # and also summarized for the runner's compact failure payload.
                failures.append((channel_input, report.error))
            reports.append(report)
        except Exception as exc:
            # Keep a defensive catch at the batch boundary. The lower layers
            # handle known failures, but this protects the rest of the batch
            # from an unexpected bug or API-client exception.
            logger.exception("Unexpected error for %s", channel_input)
            failures.append((channel_input, str(exc)))
            reports.append(ChannelReport(input_raw=channel_input, error=str(exc)))

    logger.info("Batch run complete: %s success, %s failure", total - len(failures), len(failures))
    return reports, failures


def build_channel_report(client: YouTubeClient,channel_input: str,*,include_comments: bool = True,
                         max_videos: int = 10,max_comments: int = 1000,
                         delay_ms: int = 0,video_workers: int = 1) -> ChannelReport:
    """Build a full channel report: metadata, latest N videos, and per-video comments.

    Returns:
        A :class:`ChannelReport`. On failure it still returns a report object,
        with the problem recorded in its ``error`` field rather than raising.
    """
    logger.info("Building channel report for %s", channel_input)

    # Resolve the input and load channel metadata.
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
        report.videos = [
            VideoReport(video=v, comments=[], comments_fetched=0, comments_status="skipped")
            for v in videos
        ]
        return report

    built = _build_video_reports( client, videos, max_comments=max_comments, delay_ms=delay_ms, video_workers=video_workers )

    report.videos = built
    logger.info("Channel report complete for %s: %s video(s)", channel_input, len(built))
    return report


def _build_video_reports(client: YouTubeClient,videos: list[VideoSummary],*,max_comments: int,delay_ms: int,video_workers: int) -> list[VideoReport]:
    """Build a :class:`VideoReport` for each video, sequentially or in parallel."""
    worker_count = max(video_workers, 1)

    if worker_count == 1 or len(videos) <= 1:
        built: list[VideoReport] = []
        for video in videos:
            built.append( _build_video_report_for_summary(client, video, max_comments=max_comments, delay_ms=delay_ms) )
        return built

    worker_count = min(worker_count, len(videos))
    logger.info("Processing %s video(s) with %s worker thread(s)", len(videos), worker_count)

    ordered: list[VideoReport | None] = [None] * len(videos)
    api_key = client.api_key

    with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="video-report") as executor:
        futures = {
            executor.submit(_build_video_report_in_worker, api_key, video, max_comments, delay_ms): index
            for index, video in enumerate(videos)
        }
        for future in as_completed(futures):
            index = futures[future]
            ordered[index] = future.result()

    return [report for report in ordered if report is not None]


def _build_video_report_in_worker(api_key: str, video: VideoSummary, max_comments: int, delay_ms: int) -> VideoReport:
    """Thread entry point: build a video report using a fresh, thread-local client."""
    client = YouTubeClient(api_key=api_key)
    return _build_video_report_for_summary(client, video, max_comments=max_comments, delay_ms=delay_ms)


def _build_video_report_for_summary(client: YouTubeClient,video: VideoSummary,*,max_comments: int,delay_ms: int) -> VideoReport:
    """Process one video: fetch its top-level comments and enrich the commenters."""
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
