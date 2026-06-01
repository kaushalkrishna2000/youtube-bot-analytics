"""Run channel-mode reports in batch."""

from __future__ import annotations

import logging

from core.youtube_client import YouTubeClient
from logic.report import build_channel_report
from models.records import ChannelReport

logger = logging.getLogger(__name__)


def run_batch(client: YouTubeClient, channel_inputs: list[str], *, include_comments: bool = True, max_videos: int = 10, max_comments: int = 1000, delay_ms: int = 0) -> tuple[list[ChannelReport], list[tuple[str, str]]]:
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
            )
            if report.error:
                failures.append((channel_input, report.error))
            reports.append(report)
        except Exception as exc:
            logger.exception("Unexpected error for %s", channel_input)
            failures.append((channel_input, str(exc)))
            reports.append(ChannelReport(input_raw=channel_input, error=str(exc)))

    logger.info("Batch run complete: %s success, %s failure", total - len(failures), len(failures))
    return reports, failures
