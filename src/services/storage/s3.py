"""S3 persistence helpers for full Lambda fetch outputs.

The Lambda response intentionally stays compact, but the complete runner payload
can be large because it includes videos and comments. This module builds stable
timestamp-partitioned object keys and uploads the full JSON document to S3 for
downstream ingest jobs.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def build_s3_object_key(prefix: str, request_id: str | None = None) -> str:
    """Build an immutable S3 object key for one fetch run.

    Keys are partitioned by UTC date for easy S3 browsing/lifecycle policies.
    Lambda request IDs make retries traceable; local callers receive a generated
    UUID suffix so repeated runs do not overwrite each other.
    """

    timestamp = datetime.now(timezone.utc)
    safe_prefix = prefix.strip("/")

    # Avoid overwriting: every run gets a unique suffix from Lambda context or a local UUID fallback.
    suffix = (request_id or "").strip() or f"local-{uuid.uuid4().hex}"
    return f"{safe_prefix}/{timestamp:%Y/%m/%d}/run-{timestamp:%Y%m%dT%H%M%SZ}-{suffix}.json"


def upload_fetch_result_json( payload: dict[str, Any], bucket: str, prefix: str,request_id: str | None = None ) -> dict[str, Any]:
    """Upload the full fetch payload as UTF-8 JSON.

    Returns:
        Compact upload metadata suitable for the Lambda response: bucket, key,
        S3 URI, byte size, and the S3 ETag when boto3 returns one.
    """
    import boto3

    key = build_s3_object_key(prefix, request_id)
    # Preserve non-ASCII comment/channel text in the JSON while uploading bytes
    # with an explicit UTF-8 encoding and application/json content type.
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
