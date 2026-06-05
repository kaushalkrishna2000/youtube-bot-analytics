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


# -----------------------------------------------------------------------------
# Main Flow - called by lambda_handler in this order:
#   1. load_runtime → 2. build_result → 3. resolve_work_items → 4. process_work_item → 5. finalize_result
# Note: resolve_work_items is called twice – once inside build_result (to get the count for logging) and once
# in the lambda_handler loop (to iterate). Both calls return the same list; the double call is intentional and harmless.
# -----------------------------------------------------------------------------


def load_runtime(event: dict[str, Any] | None, context: Any) -> Runtime:
    """Create the runtime dependency bundle for one channel-stage invocation.

    Args:
        event: Lambda event payload. It is accepted for handler symmetry but not
            used by the scheduled channel stage.
        context: AWS Lambda context object used to derive a stable job ID.

    Returns:
        Runtime object containing settings, clients, and writer dependencies.
    """

    # Load project settings from environment variables
    settings = load_settings()

    # Generate a stable job identifier from the Lambda context
    job_id = get_job_id(context)

    runtime = Runtime(
        settings=settings,
        job_id=job_id,
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


def resolve_work_items(runtime: Runtime) -> list[str]:
    """Return normalized channel inputs configured for this invocation.

    Args:
        runtime: Runtime bundle with loaded channel settings.

    Returns:
        Channel handles, IDs, names, or URLs stripped of empty entries.
    """
    return normalize_channel_inputs(runtime.settings.youtube_channels)


def build_result(runtime: Runtime) -> dict[str, Any]:
    """Initialize the channel-stage result payload and startup log entry.

    Args:
        runtime: Runtime bundle for the current invocation.

    Returns:
        Mutable result dictionary updated by each work item.
    """
    requested = len(resolve_work_items(runtime))
    logger.info(
        "Starting channel stage job_id=%s requested=%s bucket=%s prefix=%s ttl_days=%s delay_ms=%s",
        runtime.job_id,
        requested,
        runtime.settings.pipeline_s3_bucket,
        runtime.settings.channel_stage_prefix,
        runtime.settings.staging_ttl_days,
        runtime.settings.request_delay_ms,
    )
    return {
        "ok": True,
        "job_id": runtime.job_id,
        "stage": "channel",
        "requested": requested,
        "staged": 0,
        "mongo_upserts": 0,
        "outputs": [],
        "errors": [],
    }


def process_work_item(runtime: Runtime, result: dict[str, Any], channel_input: str) -> None:
    """Resolve, stage to S3, and upsert to MongoDB one configured channel input.

    Args:
        runtime: Runtime bundle for API, S3, and Mongo access.
        result: Mutable invocation result that receives counters and errors.
        channel_input: Raw channel identifier from configuration.
    """
    try:

        # Fetch raw channel data from the YouTube API
        channel_doc = fetch_channel_document(runtime.youtube_client, channel_input, delay_ms=runtime.settings.request_delay_ms)

        # Prepare the payload for S3 staging
        payload = build_channel_stage_payload(runtime, channel_doc)

        # Upload processed results to the S3 staging bucket
        upload = put_stage_json(
            runtime.s3_client,
            bucket=runtime.settings.pipeline_s3_bucket,
            prefix=runtime.settings.channel_stage_prefix,
            payload=payload,
        )

        result["staged"] += 1
        result["outputs"].append(dump_model(upload))

        # Sync the latest data into the MongoDB database
        mongo_upserts = runtime.mongo_writer.upsert_channel(channel_doc)

        result["mongo_upserts"] += mongo_upserts
        logger.info(
            "Staged channel input=%s channel_id=%s s3_key=%s mongo_upserts=%s",
            channel_input,
            channel_doc.channel_id,
            upload.key,
            mongo_upserts,
        )
    except Exception as exc:
        logger.exception("Failed to stage channel %s", channel_input)
        result["errors"].append({"channel_input": channel_input, "message": str(exc)})


def finalize_result(result: dict[str, Any]) -> dict[str, Any]:
    """Finalize success status and emit the channel-stage summary log.

    Args:
        result: Mutable invocation result built during processing.

    Returns:
        The same result dictionary with final ``ok`` status applied.
    """
    result["ok"] = not result["errors"]
    logger.info(
        "Finished channel stage ok=%s requested=%s staged=%s mongo_upserts=%s errors=%s",
        result["ok"],
        result["requested"],
        result["staged"],
        result["mongo_upserts"],
        len(result["errors"]),
    )
    return result


# -----------------------------------------------------------------------------
# Step Helpers
# -----------------------------------------------------------------------------


def build_channel_stage_payload(runtime: Runtime, channel: ChannelDocument) -> ChannelStagePayload:
    """Build the S3 handoff payload for a resolved channel.

    Args:
        runtime: Runtime bundle containing job and TTL settings.
        channel: Mongo-ready channel document fetched from YouTube.

    Returns:
        Channel stage payload written to the configured S3 prefix.
    """
    created_at = utc_now()
    return ChannelStagePayload(
        schema_version="2026-06-02",
        stage="channel",
        job_id=runtime.job_id,
        created_at=utc_iso(created_at),
        expires_at=utc_iso(created_at + timedelta(days=runtime.settings.staging_ttl_days)),
        channel=channel,
    )
