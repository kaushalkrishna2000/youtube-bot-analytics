"""Lambda-oriented batch channel runner (no CLI dependency)."""

from __future__ import annotations

import json
import logging
from typing import Any

from core.config import get_request_delay_ms
from core.logging import configure_logging
from core.youtube_client import YouTubeClient
from logic.batch import run_batch
from utils.basic_utils import coerce_int_with_min, normalize_nonempty_str_list

logger = logging.getLogger(__name__)


def build_lambda_response(status_code: int, payload: dict[str, Any]) -> dict[str, Any]:
    """Build API Gateway compatible Lambda response payload."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload, ensure_ascii=False),
    }


def _base_result(error: str | None = None) -> dict[str, Any]:
    return {
        "ok": False if error else True,
        "error": error,
        "summary": {"total": 0, "success": 0, "failed": 0},
        "reports": [],
        "failures": [],
        "config_used": {},
    }


def run_fetch_job(channels: list[str], *, include_comments: bool = True, max_videos: int = 10, max_comments: int = 1000, delay_ms: int | None = None, quiet: bool = False) -> dict[str, Any]:
    """Run channel batch fetch and return JSON-safe in-memory payload."""
    configure_logging(level=logging.WARNING if quiet else logging.INFO, quiet=quiet)
    logger.info("Fetch job validation started")

    if not isinstance(channels, list):
        logger.info("Fetch job validation failed: channels must be a list")
        result = _base_result("channels must be a list of strings")
        return result

    cleaned_channels = normalize_nonempty_str_list(channels)
    if not cleaned_channels:
        logger.info("Fetch job validation failed: no valid channels provided")
        result = _base_result("No valid channels provided")
        return result

    safe_max_videos, max_videos_error = coerce_int_with_min(max_videos, field_name="max_videos")
    if max_videos_error:
        logger.info("Fetch job validation failed: %s", max_videos_error)
        result = _base_result(max_videos_error)
        return result

    safe_max_comments, max_comments_error = coerce_int_with_min(max_comments, field_name="max_comments")
    if max_comments_error:
        logger.info("Fetch job validation failed: %s", max_comments_error)
        result = _base_result(max_comments_error)
        return result

    if delay_ms is None:
        resolved_delay_ms = get_request_delay_ms()
    else:
        resolved_delay_ms, delay_error = coerce_int_with_min(delay_ms, field_name="delay_ms", minimum=0)
        if delay_error:
            logger.info("Fetch job validation failed: %s", delay_error)
            result = _base_result(delay_error)
            return result
        assert resolved_delay_ms is not None

    config_used = {
        "include_comments": include_comments,
        "max_videos": safe_max_videos,
        "max_comments": safe_max_comments,
        "delay_ms": resolved_delay_ms,
        "quiet": quiet,
    }
    logger.info("Fetch job config resolved: channels=%s include_comments=%s max_videos=%s max_comments=%s delay_ms=%s quiet=%s", len(cleaned_channels), include_comments, safe_max_videos, safe_max_comments, resolved_delay_ms, quiet)

    try:
        logger.info("Initializing YouTube client")
        client = YouTubeClient()
    except ValueError as exc:
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

    reports, failures = run_batch(
        client,
        cleaned_channels,
        include_comments=include_comments,
        max_videos=safe_max_videos,
        max_comments=safe_max_comments,
        delay_ms=resolved_delay_ms,
    )

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
