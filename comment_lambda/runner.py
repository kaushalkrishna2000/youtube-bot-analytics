"""Task-based runner for comment_lambda."""

from __future__ import annotations

import logging
from datetime import timedelta

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


def load_runtime(event: dict[str, Any] | None, context: Any) -> Runtime:
    settings = load_settings()
    return Runtime(
        settings=settings,
        event=event,
        youtube_client=YouTubeClient(settings.youtube_api_key),
        s3_client=boto3.client("s3"),
        mongo_writer=MongoWriter(settings),
    )


def resolve_work_items(runtime: Runtime) -> list[dict[str, str]]:
    return parse_s3_event(runtime.event)


def build_result(runtime: Runtime) -> dict[str, Any]:
    refs = resolve_work_items(runtime)
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
    try:
        raw_payload = read_json_object(runtime.s3_client, bucket=s3_ref["bucket"], key=s3_ref["key"])
        source = VideoStagePayload.model_validate(raw_payload)
        error = None
        try:
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

        payload = build_comment_stage_payload(runtime, source, comments, comments_status=comments_status, error=error)
        upload = put_stage_json(
            runtime.s3_client,
            bucket=runtime.settings.pipeline_s3_bucket,
            prefix=runtime.settings.comment_stage_prefix,
            payload=payload,
        )

        result["comment_results_staged"] += 1
        result["outputs"].append(dump_model(upload))
        result["comments_upserted"] += runtime.mongo_writer.upsert_comments(comments)
        result["video_status_updates"] += runtime.mongo_writer.update_video_comment_status(
            source.video.video_id,
            comments_status=comments_status,
            comments_fetched=len(comments),
            error=error,
        )
    except Exception as exc:
        logger.exception("Failed to stage comments for %s/%s", s3_ref["bucket"], s3_ref["key"])
        result["errors"].append({"bucket": s3_ref["bucket"], "key": s3_ref["key"], "message": str(exc)})


def finalize_result(result: dict[str, Any]) -> dict[str, Any]:
    result["ok"] = not result["errors"]
    return result


def build_comment_stage_payload(
    runtime: Runtime,
    source: VideoStagePayload,
    comments: list[CommentDocument],
    *,
    comments_status: str,
    error: str | None,
) -> CommentStagePayload:
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
