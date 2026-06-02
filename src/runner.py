"""Lambda-oriented batch channel runner with JSON-safe return payloads.

The Lambda handler delegates fetch execution here after resolving channel input
and S3 output config. This module validates runner options, initializes the
YouTube client, calls the batch orchestration layer, and shapes the in-memory
result that is both uploaded to S3 and summarized in the Lambda response.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from core.config import get_request_delay_ms, get_video_workers
from core.logging import configure_logging
from core.youtube_client import YouTubeClient
from logic.fetcher import run_batch
from utils.basic_utils import coerce_int_with_min, normalize_nonempty_str_list
from utils.responses import build_lambda_response

logger = logging.getLogger(__name__)


def _base_result(error: str | None = None) -> dict[str, Any]:
    """Return the empty runner payload used for validation/config failures."""
    return {
        "ok": False if error else True,
        "error": error,
        "summary": {"total": 0, "success": 0, "failed": 0},
        "reports": [],
        "failures": [],
        "config_used": {},
    }


def run_fetch_job(channels: list[str],*,include_comments: bool = True,
                  max_videos: int = 10,max_comments: int = 1000,
                  delay_ms: int | None = None,video_workers: int | None = None,quiet: bool = False) -> dict[str, Any]:

    """Run a complete channel batch fetch and return a JSON-safe payload.

    Validation failures and missing API-key failures are returned as structured
    payloads instead of being raised. Per-channel failures are collected by
    ``logic.fetcher.run_batch`` so one bad channel does not discard successful
    reports from other inputs.
    """

    configure_logging(level=logging.WARNING if quiet else logging.INFO, quiet=quiet)
    logger.info("Fetch job validation started")

    # Lambda passes a normalized list, but direct callers may not. Keep this boundary strict so downstream services only receive channel strings.
    if not isinstance(channels, list):
        logger.info("Fetch job validation failed: channels must be a list")
        return _base_result("channels must be a list of strings")

    cleaned_channels = normalize_nonempty_str_list(channels)
    if not cleaned_channels:
        logger.info("Fetch job validation failed: no valid channels provided")
        return _base_result("No valid channels provided")

    # The two per-video limits share the same min-1 validation, so fold them into one pass; the first bad value short-circuits with its error payload.
    resolved_limits: dict[str, int] = {}
    for field_name, raw_value in (("max_videos", max_videos), ("max_comments", max_comments)):
        number, error = coerce_int_with_min(raw_value, field_name=field_name)
        if error:
            logger.info("Fetch job validation failed: %s", error)
            return _base_result(error)
        assert number is not None
        resolved_limits[field_name] = number
    safe_max_videos = resolved_limits["max_videos"]
    safe_max_comments = resolved_limits["max_comments"]

    if delay_ms is None:
        # None means "use environment/default"; an explicit value is validated below so callers can override the Lambda-level throttle.
        resolved_delay_ms = get_request_delay_ms()
    else:
        resolved_delay_ms, delay_error = coerce_int_with_min(delay_ms, field_name="delay_ms", minimum=0)
        if delay_error:
            logger.info("Fetch job validation failed: %s", delay_error)
            return _base_result(delay_error)
        assert resolved_delay_ms is not None

    if video_workers is None:
        # Worker count mirrors delay handling: omitted uses environment/default, explicit values are normalized to at least one worker.
        resolved_video_workers = get_video_workers()
    else:
        resolved_video_workers, workers_error = coerce_int_with_min(video_workers, field_name="video_workers")
        if workers_error:
            logger.info("Fetch job validation failed: %s", workers_error)
            return _base_result(workers_error)
        assert resolved_video_workers is not None

    config_used = {
        "include_comments": include_comments,
        "max_videos": safe_max_videos,
        "max_comments": safe_max_comments,
        "delay_ms": resolved_delay_ms,
        "video_workers": resolved_video_workers,
        "quiet": quiet,
    }
    logger.info(
        "Fetch job config resolved: channels=%s include_comments=%s max_videos=%s max_comments=%s delay_ms=%s video_workers=%s quiet=%s",
        len(cleaned_channels),
        include_comments,
        safe_max_videos,
        safe_max_comments,
        resolved_delay_ms,
        resolved_video_workers,
        quiet,
    )

    try:
        logger.info("Initializing YouTube client")
        client = YouTubeClient()
    except ValueError as exc:
        # Missing API key prevents all channel work. Preserve each input in the
        # failure list so the caller can see the full requested batch.
        logger.info("YouTube client initialization failed: %s", exc)
        failures = [{"channel_input": item, "error": str(exc)} for item in cleaned_channels]
        return {
            "ok": False,
            "error": str(exc),
            "summary": {"total": len(cleaned_channels), "success": 0, "failed": len(cleaned_channels)},
            "reports": [],
            "failures": failures,
            "config_used": config_used,
        }
    logger.info("YouTube client initialized")

    reports, failures = run_batch( client, cleaned_channels,
                                   include_comments=include_comments, max_videos=safe_max_videos,
                                   max_comments=safe_max_comments, delay_ms=resolved_delay_ms,
                                   video_workers=resolved_video_workers
                                   )

    # Convert internal tuples to the public failure shape used by Lambda/S3.
    failure_payload = [{"channel_input": channel_input, "error": error} for channel_input, error in failures]
    total = len(cleaned_channels)
    failed = len(failure_payload)
    success = total - failed
    logger.info("Fetch job finished: total=%s success=%s failed=%s", total, success, failed)

    return {
        "ok": failed == 0,
        "summary": {"total": total, "success": success, "failed": failed},
        "reports": [report.to_dict() for report in reports],
        "failures": failure_payload,
        "config_used": config_used,
    }
