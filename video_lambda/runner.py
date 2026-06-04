"""Task-based runner for video_lambda."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import boto3

from video_job.client import MongoWriter, YouTubeClient, put_stage_json, read_json_object
from video_job.config import load_settings
from video_job.model import ChannelStagePayload, Runtime, VideoDocument, VideoStagePayload, dump_model
from video_job.utils import fetch_latest_video_documents, parse_s3_event, utc_iso, utc_now

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Main Flow – called by lambda_handler in this order:
#   1. load_runtime → 2. build_result → 3. resolve_work_items → 4. process_work_item → 5. finalize_result
# Note: resolve_work_items is called twice – once inside build_result (to get the count for logging) and once
# in the lambda_handler loop (to iterate). Both calls return the same list; the double call is intentional and harmless.
# -----------------------------------------------------------------------------


def load_runtime(event: dict[str, Any] | None, context: Any) -> Runtime:
    """Create the runtime dependency bundle for one video-stage invocation.

    Args:
        event: S3 event payload with channel-stage object references.
        context: AWS Lambda context object. It is accepted for handler symmetry.

    Returns:
        Runtime object containing settings, event data, clients, and writer
        dependencies.
    """

    # Load project settings from environment variables
    settings = load_settings()

    return Runtime(
        settings=settings,
        event=event,
        # Initialize YouTube API client with project settings
        youtube_client=YouTubeClient(settings.youtube_api_key),

        # Standard boto3 client for S3 staging operations
        s3_client=boto3.client("s3"),

        # Specialized writer for MongoDB persistence
        mongo_writer=MongoWriter(settings),

    )


def resolve_work_items(runtime: Runtime) -> list[dict[str, str]]:
    """Extract S3 object references from the invocation event.

    Args:
        runtime: Runtime bundle containing the raw Lambda event.

    Returns:
        List of dictionaries with ``bucket`` and ``key`` values.
    """
    return parse_s3_event(runtime.event)


def build_result(runtime: Runtime) -> dict[str, Any]:
    """Initialize the video-stage result payload and startup log entry.

    Args:
        runtime: Runtime bundle for the current invocation.

    Returns:
        Mutable result dictionary updated as channel-stage objects are processed.
    """
    refs = resolve_work_items(runtime)
    logger.info(
        "Starting video stage processed=%s bucket=%s prefix=%s max_videos=%s ttl_days=%s delay_ms=%s",
        len(refs),
        runtime.settings.pipeline_s3_bucket,
        runtime.settings.video_stage_prefix,
        runtime.settings.max_videos,
        runtime.settings.staging_ttl_days,
        runtime.settings.request_delay_ms,
    )
    return {
        "ok": True,
        "stage": "video",
        "processed": len(refs),
        "videos_staged": 0,
        "mongo_upserts": 0,
        "outputs": [],
        "errors": [],
    }


def process_work_item(runtime: Runtime, result: dict[str, Any], s3_ref: dict[str, str]) -> None:
    """Resolve channel source, stage videos to S3, and upsert to MongoDB.

    Args:
        runtime: Runtime bundle for S3, YouTube, and Mongo access.
        result: Mutable invocation result that receives counters and errors.
        s3_ref: S3 object reference containing ``bucket`` and ``key``.
    """
    try:

        # Fetch the raw channel-stage payload from S3
        raw_payload = read_json_object(runtime.s3_client, bucket=s3_ref["bucket"], key=s3_ref["key"])

        source = ChannelStagePayload.model_validate(raw_payload)

        # Fetch raw video documents from the YouTube API
        videos = fetch_latest_video_documents(
            runtime.youtube_client,
            source.channel.channel_id,
            max_videos=runtime.settings.max_videos,
            delay_ms=runtime.settings.request_delay_ms,
        )

        # Prepare the payload for S3 staging
        stage_payloads = [build_video_stage_payload(runtime, source, video) for video in videos]

        # Upload processed results to the S3 staging bucket
        uploads = [
            put_stage_json(
                runtime.s3_client,
                bucket=runtime.settings.pipeline_s3_bucket,
                prefix=runtime.settings.video_stage_prefix,
                payload=payload,
            )
            for payload in stage_payloads
        ]

        result["videos_staged"] += len(uploads)
        result["outputs"].extend(dump_model(upload) for upload in uploads)

        # Sync the latest data into the MongoDB database
        mongo_upserts = runtime.mongo_writer.upsert_videos(videos)

        result["mongo_upserts"] += mongo_upserts
        logger.info(
            "Processed channel-stage source=%s/%s channel_id=%s videos_found=%s videos_staged=%s mongo_upserts=%s",
            s3_ref["bucket"],
            s3_ref["key"],
            source.channel.channel_id,
            len(videos),
            len(uploads),
            mongo_upserts,
        )
    except Exception as exc:
        logger.exception("Failed to stage videos for %s/%s", s3_ref["bucket"], s3_ref["key"])
        result["errors"].append({"bucket": s3_ref["bucket"], "key": s3_ref["key"], "message": str(exc)})


def finalize_result(result: dict[str, Any]) -> dict[str, Any]:
    """Finalize success status and emit the video-stage summary log.

    Args:
        result: Mutable invocation result built during processing.

    Returns:
        The same result dictionary with final ``ok`` status applied.
    """
    result["ok"] = not result["errors"]
    logger.info(
        "Finished video stage ok=%s processed=%s videos_staged=%s mongo_upserts=%s errors=%s",
        result["ok"],
        result["processed"],
        result["videos_staged"],
        result["mongo_upserts"],
        len(result["errors"]),
    )
    return result


# -----------------------------------------------------------------------------
# Step Helpers
# -----------------------------------------------------------------------------


def build_video_stage_payload(runtime: Runtime, source: ChannelStagePayload, video: VideoDocument) -> VideoStagePayload:
    """Build the S3 handoff payload for one hydrated video.

    Args:
        runtime: Runtime bundle containing TTL settings.
        source: Channel-stage payload that produced the video.
        video: Mongo-ready video document fetched from YouTube.

    Returns:
        Video stage payload written to the configured S3 prefix.
    """
    created_at = utc_now()
    return VideoStagePayload(
        schema_version="2026-06-02",
        stage="video",
        job_id=source.job_id,
        created_at=utc_iso(created_at),
        expires_at=utc_iso(created_at + timedelta(days=runtime.settings.staging_ttl_days)),
        channel=source.channel,
        video=video,
    )
