"""S3 staging helpers for video_lambda."""

from __future__ import annotations

import json
from typing import Any

from video_job.model import UploadMetadata, VideoStagePayload, dump_model
from video_job.utils.text import slug


def read_json_object(s3_client: Any, *, bucket: str, key: str) -> dict[str, Any]:
    """Read a staged JSON object from S3.

    Args:
        s3_client: Boto3 S3 client or compatible test double.
        bucket: Source bucket name.
        key: Source object key.

    Returns:
        Decoded JSON object.

    Raises:
        ValueError: If the staged payload is not a JSON object.
    """
    response = s3_client.get_object(Bucket=bucket, Key=key)
    body = response["Body"].read()
    data = json.loads(body.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Staged S3 payload must be a JSON object")
    return data


def put_stage_json(s3_client: Any, *, bucket: str, prefix: str, payload: VideoStagePayload) -> UploadMetadata:
    """Write a video-stage payload as compact JSON to S3.

    Args:
        s3_client: Boto3 S3 client or compatible test double.
        bucket: Destination bucket name.
        prefix: Destination key prefix without a trailing slash requirement.
        payload: Video-stage payload to serialize.

    Returns:
        Metadata describing the uploaded S3 object.
    """
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


def _video_key(prefix: str, job_id: str, _channel_id: str, video_id: str) -> str:
    """Build the flat S3 key for one video payload."""
    return f"{prefix}/{slug(video_id)}-{slug(job_id)}.json"
