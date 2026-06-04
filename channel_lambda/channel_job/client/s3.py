"""S3 staging helpers for channel_lambda."""

from __future__ import annotations

import json
from typing import Any

from channel_job.model import ChannelStagePayload, UploadMetadata
from channel_job.utils.text import slug


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------


def put_stage_json(s3_client: Any, *, bucket: str, prefix: str, payload: ChannelStagePayload) -> UploadMetadata:

    # Build the unique S3 key for this channel payload
    key = _channel_key(prefix, payload.job_id, payload.channel.channel_id)

    # Serialize the payload to a compact JSON byte string
    body = json.dumps(payload.model_dump(mode="json", exclude_none=False), ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    # Upload the JSON object to S3 with associated metadata
    response = s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=body,
        ContentType="application/json",
        Metadata={"stage": payload.stage, "job_id": payload.job_id, "expires_at": payload.expires_at},
    )

    # Return structured metadata about the uploaded object
    return UploadMetadata(
        bucket=bucket,
        key=key,
        s3_uri=f"s3://{bucket}/{key}",
        size_bytes=len(body),
        etag=response.get("ETag") if isinstance(response, dict) else None,
    )


# -----------------------------------------------------------------------------
# Private Helpers
# -----------------------------------------------------------------------------


def _channel_key(prefix: str, job_id: str, channel_id: str) -> str:

    # Combine prefix, channel ID, and job ID into a slugified key
    return f"{prefix}/{slug(channel_id)}-{slug(job_id)}.json"
