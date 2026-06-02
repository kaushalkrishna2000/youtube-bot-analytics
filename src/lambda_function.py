"""AWS Lambda entrypoint for the YouTube batch fetch job.

The handler keeps Lambda-specific concerns at the edge: channel input selection,
S3 destination validation, response status codes, and upload error handling.
Actual fetching is delegated to ``runner.run_fetch_job`` so the same
runner can be exercised locally or by tests without AWS event plumbing.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from core.config import get_configured_channels, get_s3_output_config
from services.storage.s3 import upload_fetch_result_json
from runner import run_fetch_job
from utils.responses import build_lambda_response

logger = logging.getLogger(__name__)

def lambda_handler(event: dict[str, Any] | None, context: Any) -> dict[str, Any]:
    """Run one fetch invocation and upload the full result to S3.

    Args:
        event: Currently unused. Kept for AWS Lambda handler compatibility.
        context: AWS Lambda context. ``aws_request_id`` is used as part of the
            S3 object key when available.

    Returns:
        API Gateway-style response envelope with a JSON string body. The full
        report payload is uploaded to S3; the response only includes summary,
        failures, resolved config, and upload metadata.
    """
    # event is intentionally unused; context contributes the AWS request id for immutable S3 object names and easier CloudWatch/S3 correlation.
    request_id = getattr(context, "aws_request_id", None)
    logger.info("Lambda fetch invocation started request_id=%s", request_id or "unavailable")

    channels = get_configured_channels()

    logger.info("Resolved %s channel input(s)", len(channels))
    if not channels:
        logger.info("Lambda fetch returning 400: no channels configured")
        return build_lambda_response(400,{ "ok": False, "error": "No channels configured. Set YOUTUBE_CHANNELS env var."} )

    try:
        bucket, prefix = get_s3_output_config()
    except ValueError as exc:
        # Without an output bucket, running the fetch would produce data the
        # Lambda cannot persist. Fail before spending YouTube API quota.
        logger.info("Lambda fetch returning 500: S3 output config error: %s", exc)
        return build_lambda_response(500,{  "ok": False, "error": str(exc) } )

    logger.info("Resolved S3 output destination bucket=%s prefix=%s", bucket, prefix)

    logger.info("Starting fetch job for %s channel input(s)", len(channels))
    result = run_fetch_job(channels, max_videos=20, max_comments=2000, quiet=False)
    logger.info("Fetch job completed summary=%s ok=%s", result.get("summary", {}), result.get("ok", False))

    try:
        logger.info("Starting S3 upload for fetch result request_id=%s", request_id or "unavailable")
        upload = upload_fetch_result_json(result, bucket, prefix, str(request_id) if request_id else None)
    except Exception as exc:
        # Return the fetch summary even when persistence fails; it is useful for operators debugging whether the YouTube side succeeded.
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

    # Keep Lambda responses compact. Large nested reports live in the uploaded S3 object and are intentionally excluded from the response body.
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
