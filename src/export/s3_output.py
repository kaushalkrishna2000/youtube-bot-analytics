"""S3 persistence helpers for Lambda fetch outputs."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def build_s3_object_key(prefix: str, request_id: str | None = None) -> str:
    """Build an immutable, timestamp-partitioned S3 object key."""
    timestamp = datetime.now(timezone.utc)
    safe_prefix = prefix.strip("/")
    suffix = (request_id or "").strip() or f"local-{uuid.uuid4().hex}"
    return (
        f"{safe_prefix}/{timestamp:%Y/%m/%d}/"
        f"run-{timestamp:%Y%m%dT%H%M%SZ}-{suffix}.json"
    )


def upload_fetch_result_json(payload: dict[str, Any], bucket: str, prefix: str, request_id: str | None = None) -> dict[str, Any]:
    """Upload the full fetch payload as UTF-8 JSON and return compact upload metadata."""
    import boto3

    key = build_s3_object_key(prefix, request_id)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    client = boto3.client("s3")

    logger.info("Generated S3 output key=%s", key)
    logger.info("Uploading fetch output to S3 bucket=%s key=%s size_bytes=%s", bucket, key, len(body))
    response = client.put_object(Bucket=bucket, Key=key, Body=body, ContentType="application/json")

    upload = {
        "bucket": bucket,
        "key": key,
        "s3_uri": f"s3://{bucket}/{key}",
        "size_bytes": len(body),
    }
    etag = response.get("ETag") if isinstance(response, dict) else None
    if etag:
        upload["etag"] = etag
    logger.info("Fetch output upload succeeded s3_uri=%s size_bytes=%s etag_present=%s", upload["s3_uri"], upload["size_bytes"], bool(etag))
    return upload
