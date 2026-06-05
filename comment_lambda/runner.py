"""Task-based runner for comment_lambda."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import boto3

from comment_job.client import MongoWriter, YouTubeClient, put_stage_json, read_json_object
from comment_job.config import load_settings
from comment_job.model import CommentDocument, CommentStagePayload, Runtime, VideoStagePayload, dump_model
from comment_job.utils import (
    CommentsDisabledError,
    fetch_comment_documents,
    parse_s3_event,
    utc_iso,
    utc_now,
)

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Main Flow  –  called by lambda_handler in this order:
#   1. load_runtime  →  2. build_result  →  3. resolve_work_items  →  4. process_work_item  →  5. finalize_result
# Note: resolve_work_items is called twice – once inside build_result (to get the count for logging) and once
# in the lambda_handler loop (to iterate). Both calls return the same list; the double call is intentional and harmless.
# -----------------------------------------------------------------------------


def load_runtime(event: dict[str, Any] | None, context: Any) -> Runtime:
    """Create the runtime dependency bundle for one comment-stage invocation.

    Args:
        event: S3 event payload with video-stage object references.
        context: AWS Lambda context object. It is accepted for handler symmetry.

    Returns:
        Runtime object containing settings, event data, clients, and writer
        dependencies.
    """

    # Load project settings from environment variables
    settings = load_settings()

    runtime = Runtime(
        settings=settings,
        event=event,
        # Initialize YouTube API client with project settings
        youtube_client=YouTubeClient(settings.youtube_api_key),

        # Standard boto3 client for S3 staging operations
        s3_client=boto3.client("s3"),

        # Specialized writer for MongoDB persistence
        mongo_writer=MongoWriter(settings),

    )

    # Confirm successful cold-start initialisation
    logger.info(
        "Runtime initialised youtube_api_key_set=%s mongo_db=%s",
        bool(settings.youtube_api_key),
        settings.mongo_db_name,
    )

    return runtime


def resolve_work_items(runtime: Runtime) -> list[dict[str, str]]:
    """Extract S3 object references from the invocation event.

    Args:
        runtime: Runtime bundle containing the raw Lambda event.

    Returns:
        List of dictionaries with ``bucket`` and ``key`` values.
    """
    return parse_s3_event(runtime.event)


def build_result(runtime: Runtime) -> dict[str, Any]:
    """Initialize the comment-stage result payload and startup log entry.

    Args:
        runtime: Runtime bundle for the current invocation.

    Returns:
        Mutable result dictionary updated as video-stage objects are processed.
    """
    refs = resolve_work_items(runtime)
    logger.info(
        "Starting comment stage processed=%s bucket=%s prefix=%s max_comments=%s ttl_days=%s delay_ms=%s",
        len(refs),
        runtime.settings.pipeline_s3_bucket,
        runtime.settings.comment_stage_prefix,
        runtime.settings.max_comments,
        runtime.settings.staging_ttl_days,
        runtime.settings.request_delay_ms,
    )
    return {
        "ok": True,
        "stage": "comment",
        "processed": len(refs),
        "comment_results_staged": 0,
        "comments_upserted": 0,
        "video_status_updates": 0,
        "outputs": [],
        "errors": [],
    }


def process_work_item(runtime: Runtime, result: dict[str, Any], s3_ref: dict[str, str]) -> None:
    """Resolve video source, stage comments to S3, and upsert to MongoDB.

    Args:
        runtime: Runtime bundle for S3, YouTube, and Mongo access.
        result: Mutable invocation result that receives counters and errors.
        s3_ref: S3 object reference containing ``bucket`` and ``key``.
    """
    try:

        # Fetch the raw video-stage payload from S3
        raw_payload = read_json_object(runtime.s3_client, bucket=s3_ref["bucket"], key=s3_ref["key"])

        source = VideoStagePayload.model_validate(raw_payload)
        error = None
        try:

            # Fetch raw comment documents from the YouTube API
            comments, comments_status = fetch_comment_documents(
                runtime.youtube_client,
                channel_id=source.channel.channel_id,
                video_id=source.video.video_id,
                max_comments=runtime.settings.max_comments,
                delay_ms=runtime.settings.request_delay_ms,
            )

        except CommentsDisabledError as exc:
            comments = []
            comments_status = "disabled"
            error = str(exc)
            logger.info(
                "Comments disabled channel_id=%s video_id=%s source=%s/%s",
                source.channel.channel_id,
                source.video.video_id,
                s3_ref["bucket"],
                s3_ref["key"],
            )

        # Prepare the payload for S3 staging
        payload = build_comment_stage_payload(runtime, source, comments, comments_status=comments_status, error=error)

        # Upload processed results to the S3 staging bucket
        upload = put_stage_json(
            runtime.s3_client,
            bucket=runtime.settings.pipeline_s3_bucket,
            prefix=runtime.settings.comment_stage_prefix,
            payload=payload,
        )

        result["comment_results_staged"] += 1
        result["outputs"].append(dump_model(upload))

        # Sync the latest data into the MongoDB database
        comments_upserted = runtime.mongo_writer.upsert_comments(comments)

        # Update the video status to reflect current comment availability
        video_status_updates = runtime.mongo_writer.update_video_comment_status(
            source.video.video_id,
            comments_status=comments_status,
            comments_fetched=len(comments),
            error=error,
        )

        result["comments_upserted"] += comments_upserted
        result["video_status_updates"] += video_status_updates
        logger.info(
            "Processed video-stage source=%s/%s channel_id=%s video_id=%s comments_status=%s comments_fetched=%s s3_key=%s comments_upserted=%s video_status_updates=%s",
            s3_ref["bucket"],
            s3_ref["key"],
            source.channel.channel_id,
            source.video.video_id,
            comments_status,
            len(comments),
            upload.key,
            comments_upserted,
            video_status_updates,
        )
    except Exception as exc:
        logger.exception("Failed to stage comments for %s/%s", s3_ref["bucket"], s3_ref["key"])
        result["errors"].append({"bucket": s3_ref["bucket"], "key": s3_ref["key"], "message": str(exc)})


def finalize_result(result: dict[str, Any]) -> dict[str, Any]:
    """Finalize success status and emit the comment-stage summary log.

    Args:
        result: Mutable invocation result built during processing.

    Returns:
        The same result dictionary with final ``ok`` status applied.
    """
    result["ok"] = not result["errors"]
    logger.info(
        "Finished comment stage ok=%s processed=%s comment_results_staged=%s comments_upserted=%s video_status_updates=%s errors=%s",
        result["ok"],
        result["processed"],
        result["comment_results_staged"],
        result["comments_upserted"],
        result["video_status_updates"],
        len(result["errors"]),
    )
    return result


# -----------------------------------------------------------------------------
# Step Helpers
# -----------------------------------------------------------------------------


def build_comment_stage_payload(
    runtime: Runtime,
    source: VideoStagePayload,
    comments: list,
    *,
    comments_status: str,
    error: str | None,
) -> CommentStagePayload:
    """Build the S3 handoff payload for fetched comments on one video.

    Args:
        runtime: Runtime bundle containing TTL settings.
        source: Video-stage payload that produced the comment fetch.
        comments: Mongo-ready comment documents fetched from YouTube.
        comments_status: Fetch outcome such as ``ok``, ``none``, ``partial``,
            or ``disabled``.
        error: Optional error message stored when comments are disabled.

    Returns:
        Comment stage payload written to the configured S3 prefix.
    """
    created_at = utc_now()
    return CommentStagePayload(
        schema_version="2026-06-02",
        stage="comment",
        job_id=source.job_id,
        created_at=utc_iso(created_at),
        expires_at=utc_iso(created_at + timedelta(days=runtime.settings.staging_ttl_days)),
        channel=source.channel,
        video=source.video,
        comments_status=comments_status,
        comments_fetched=len(comments),
        comments=comments,
        error=error,
    )
