"""Task-based runner for channel_lambda."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import boto3

from channel_job.client import MongoWriter, YouTubeClient, put_stage_json
from channel_job.config import load_settings
from channel_job.model import ChannelDocument, ChannelStagePayload, Runtime, dump_model
from channel_job.utils import (
    fetch_channel_document,
    get_job_id,
    normalize_channel_inputs,
    utc_iso,
    utc_now,
)

logger = logging.getLogger(__name__)


def load_runtime(event: dict[str, Any] | None, context: Any) -> Runtime:
    settings = load_settings()
    job_id = get_job_id(context)
    return Runtime(
        settings=settings,
        job_id=job_id,
        youtube_client=YouTubeClient(settings.youtube_api_key),
        s3_client=boto3.client("s3"),
        mongo_writer=MongoWriter(settings),
    )


def resolve_work_items(runtime: Runtime) -> list[str]:
    return normalize_channel_inputs(runtime.settings.youtube_channels)


def build_result(runtime: Runtime) -> dict[str, Any]:
    return {
        "ok": True,
        "job_id": runtime.job_id,
        "stage": "channel",
        "requested": len(resolve_work_items(runtime)),
        "staged": 0,
        "mongo_upserts": 0,
        "outputs": [],
        "errors": [],
    }


def process_work_item(runtime: Runtime, result: dict[str, Any], channel_input: str) -> None:
    try:
        channel_doc = fetch_channel_document(runtime.youtube_client, channel_input, delay_ms=runtime.settings.request_delay_ms)
        payload = build_channel_stage_payload(runtime, channel_doc)
        upload = put_stage_json(
            runtime.s3_client,
            bucket=runtime.settings.pipeline_s3_bucket,
            prefix=runtime.settings.channel_stage_prefix,
            payload=payload,
        )
        result["staged"] += 1
        result["outputs"].append(dump_model(upload))
        result["mongo_upserts"] += runtime.mongo_writer.upsert_channel(channel_doc)
    except Exception as exc:
        logger.exception("Failed to stage channel %s", channel_input)
        result["errors"].append({"channel_input": channel_input, "message": str(exc)})


def finalize_result(result: dict[str, Any]) -> dict[str, Any]:
    result["ok"] = not result["errors"]
    return result


def build_channel_stage_payload(runtime: Runtime, channel: ChannelDocument) -> ChannelStagePayload:
    created_at = utc_now()
    return ChannelStagePayload(
        schema_version="2026-06-02",
        stage="channel",
        job_id=runtime.job_id,
        created_at=utc_iso(created_at),
        expires_at=utc_iso(created_at + timedelta(days=runtime.settings.staging_ttl_days)),
        channel=channel,
    )
