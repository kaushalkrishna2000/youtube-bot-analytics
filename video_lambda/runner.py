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
        "stage": "video",
        "processed": len(refs),
        "videos_staged": 0,
        "mongo_upserts": 0,
        "outputs": [],
        "errors": [],
    }


def process_work_item(runtime: Runtime, result: dict[str, Any], s3_ref: dict[str, str]) -> None:
    try:
        raw_payload = read_json_object(runtime.s3_client, bucket=s3_ref["bucket"], key=s3_ref["key"])
        source = ChannelStagePayload.model_validate(raw_payload)
        videos = fetch_latest_video_documents(
            runtime.youtube_client,
            source.channel.channel_id,
            max_videos=runtime.settings.max_videos,
            delay_ms=runtime.settings.request_delay_ms,
        )
        stage_payloads = [build_video_stage_payload(runtime, source, video) for video in videos]
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
        result["mongo_upserts"] += runtime.mongo_writer.upsert_videos(videos)
    except Exception as exc:
        logger.exception("Failed to stage videos for %s/%s", s3_ref["bucket"], s3_ref["key"])
        result["errors"].append({"bucket": s3_ref["bucket"], "key": s3_ref["key"], "message": str(exc)})


def finalize_result(result: dict[str, Any]) -> dict[str, Any]:
    result["ok"] = not result["errors"]
    return result


def build_video_stage_payload(runtime: Runtime, source: ChannelStagePayload, video: VideoDocument) -> VideoStagePayload:
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
