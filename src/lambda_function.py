"""AWS Lambda entrypoint for channel batch fetch (lightweight wrapper)."""

from __future__ import annotations

import logging
import os
from typing import Any

from core.config import get_s3_output_config
from export.s3_output import upload_fetch_result_json
from lambda_runner import build_lambda_response, run_fetch_job
from utils.basic_utils import normalize_nonempty_str_list

logger = logging.getLogger(__name__)

# Optional direct in-code channel list. If empty, YOUTUBE_CHANNELS is used.
DEFAULT_CHANNELS: list[str] = []


def lambda_handler(event: dict[str, Any] | None, context: Any) -> dict[str, Any]:
    # event is intentionally unused; context contributes the AWS request id for S3 object names.
    request_id = getattr(context, "aws_request_id", None)
    logger.info("Lambda fetch invocation started request_id=%s", request_id or "unavailable")

    if DEFAULT_CHANNELS:
        logger.info("Resolving channels from DEFAULT_CHANNELS")
        channels = normalize_nonempty_str_list(DEFAULT_CHANNELS)
    else:
        logger.info("Resolving channels from YOUTUBE_CHANNELS env var")
        raw_env = os.getenv("YOUTUBE_CHANNELS", "")
        channels = normalize_nonempty_str_list(raw_env.split(",")) if raw_env.strip() else []

    logger.info("Resolved %s channel input(s)", len(channels))
    if not channels:
        logger.info("Lambda fetch returning 400: no channels configured")
        return build_lambda_response(
            400,
            {
                "ok": False,
                "error": "No channels configured. Set DEFAULT_CHANNELS in code or YOUTUBE_CHANNELS env var.",
            },
        )

    try:
        bucket, prefix = get_s3_output_config()
    except ValueError as exc:
        logger.info("Lambda fetch returning 500: S3 output config error: %s", exc)
        return build_lambda_response(
            500,
            {
                "ok": False,
                "error": str(exc),
            },
        )
    logger.info("Resolved S3 output destination bucket=%s prefix=%s", bucket, prefix)

    logger.info("Starting fetch job for %s channel input(s)", len(channels))
    result = run_fetch_job(channels, max_videos=20, max_comments=2000, quiet=False)
    logger.info("Fetch job completed summary=%s ok=%s", result.get("summary", {}), result.get("ok", False))

    try:
        logger.info("Starting S3 upload for fetch result request_id=%s", request_id or "unavailable")
        upload = upload_fetch_result_json(result, bucket, prefix, str(request_id) if request_id else None)
    except Exception as exc:
        logger.info("Lambda fetch returning 500: S3 upload failed: %s", exc)
        return build_lambda_response(
            500,
            {
                "ok": False,
                "error": f"Failed to upload fetch output to S3: {exc}",
                "summary": result.get("summary", {}),
                "failures": result.get("failures", []),
                "config_used": result.get("config_used", {}),
                "upload": None,
            },
        )
    logger.info("S3 upload completed s3_uri=%s size_bytes=%s", upload.get("s3_uri"), upload.get("size_bytes"))

    payload = {
        "ok": result.get("ok", False),
        "summary": result.get("summary", {}),
        "failures": result.get("failures", []),
        "config_used": result.get("config_used", {}),
        "upload": upload,
    }

    if result.get("error"):
        payload["error"] = result["error"]

    logger.info("Lambda fetch returning 200 ok=%s summary=%s", payload["ok"], payload["summary"])
    return build_lambda_response(200, payload)
