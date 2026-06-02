"""S3 staging helpers for video_lambda."""

from __future__ import annotations

import json
from typing import Any

from video_job.model import UploadMetadata, VideoStagePayload, dump_model
from video_job.utils.text import slug
from video_job.utils.time import utc_now


def read_json_object(s3_client: Any, *, bucket: str, key: str) -> dict[str, Any]:
    response = s3_client.get_object(Bucket=bucket, Key=key)
    body = response["Body"].read()
    data = json.loads(body.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Staged S3 payload must be a JSON object")
    return data


def put_stage_json(s3_client: Any, *, bucket: str, prefix: str, payload: VideoStagePayload) -> UploadMetadata:
    key = _video_key(prefix, payload.job_id, payload.channel.channel_id, payload.video.video_id)
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


def _video_key(prefix: str, job_id: str, channel_id: str, video_id: str) -> str:
    now = utc_now()
    return f"{prefix}/{now:%Y/%m/%d}/{job_id}/{slug(channel_id)}/{slug(video_id)}.json"
