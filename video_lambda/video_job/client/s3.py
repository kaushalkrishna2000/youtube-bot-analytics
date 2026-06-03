"""S3 staging helpers for video_lambda."""

from __future__ import annotations

import json
from typing import Any

from video_job.model import UploadMetadata, VideoStagePayload, dump_model
from video_job.utils.text import slug


def read_json_object(s3_client: Any, *, bucket: str, key: str) -> dict[str, Any]:

    # Retrieve the object from S3 using the provided bucket and key
    response = s3_client.get_object(Bucket=bucket, Key=key)

    # Read the object body content into memory
    body = response["Body"].read()

    # Decode the byte string to UTF-8 and parse as a JSON object
    data = json.loads(body.decode("utf-8"))

    # Validate that the parsed data is a dictionary
    if not isinstance(data, dict):

        # Raise an error if the payload structure is unexpected
        raise ValueError("Staged S3 payload must be a JSON object")

    # Return the parsed JSON dictionary
    return data


def put_stage_json(s3_client: Any, *, bucket: str, prefix: str, payload: VideoStagePayload) -> UploadMetadata:

    # Build the unique S3 key for this video payload
    key = _video_key(prefix, payload.job_id, payload.channel.channel_id, payload.video.video_id)

    # Serialize the payload to a compact JSON byte string
    body = json.dumps(dump_model(payload), ensure_ascii=False, separators=(",", ":")).encode("utf-8")

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


def _video_key(prefix: str, job_id: str, _channel_id: str, video_id: str) -> str:

    # Combine prefix, video ID, and job ID into a slugified key
    return f"{prefix}/{slug(video_id)}-{slug(job_id)}.json"
