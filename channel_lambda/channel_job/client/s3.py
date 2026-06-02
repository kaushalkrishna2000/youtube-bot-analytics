"""S3 staging helpers for channel_lambda."""

from __future__ import annotations

import json
from typing import Any

from channel_job.model import ChannelStagePayload, UploadMetadata, dump_model
from channel_job.utils.text import slug
from channel_job.utils.time import utc_now


def put_stage_json(s3_client: Any, *, bucket: str, prefix: str, payload: ChannelStagePayload) -> UploadMetadata:
    key = _channel_key(prefix, payload.job_id, payload.channel.channel_id)
    body = json.dumps(dump_model(payload), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    response = s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=body,
        ContentType="application/json",
        Metadata={"stage": payload.stage, "job_id": payload.job_id, "expires_at": payload.expires_at},
    )
    return UploadMetadata(
        bucket=bucket,
        key=key,
        s3_uri=f"s3://{bucket}/{key}",
        size_bytes=len(body),
        etag=response.get("ETag") if isinstance(response, dict) else None,
    )


def _channel_key(prefix: str, job_id: str, channel_id: str) -> str:
    now = utc_now()
    return f"{prefix}/{now:%Y/%m/%d}/{job_id}/{slug(channel_id)}.json"
