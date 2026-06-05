"""AWS Lambda entrypoint for S3-triggered video staging."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

# Add local directory to path for module discovery in AWS
sys.path.insert(0, str(Path(__file__).resolve().parent))

from video_job.config import configure_logging

# Check for package context to determine import style
if __package__:

    # Use relative imports for local package execution
    from .runner import build_result, finalize_result, load_runtime, process_work_item, resolve_work_items

else:

    # Use absolute imports for flat AWS Lambda structure
    from runner import build_result, finalize_result, load_runtime, process_work_item, resolve_work_items

configure_logging()
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Lambda entrypoint
# -----------------------------------------------------------------------------


def lambda_handler(event: dict[str, Any] | None, context: Any) -> dict[str, Any]:
    """Run the S3-triggered video staging Lambda.

    Args:
        event: S3 event payload containing channel-stage objects to process.
        context: AWS Lambda context object. It is accepted for AWS compatibility
            and local runner symmetry.

    Returns:
        Result dictionary containing processed inputs, staged video outputs, and
        any per-object errors.
    """
    runtime = None
    try:

        # Log the Lambda invocation for CloudWatch traceability
        logger.info("Lambda invoked function=%s request_id=%s", context.function_name, context.aws_request_id)

        # Prepare dependencies and configuration
        runtime = load_runtime(event, context)

        # Initialize the result dictionary for tracking progress
        result = build_result(runtime)

        # Resolve work items and log if none are found
        work_items = resolve_work_items(runtime)
        if not work_items:
            logger.info("No work items resolved — nothing to process")

        # Loop through each work item identified from the event
        for s3_ref in work_items:

            # Execute the core logic for each individual item
            process_work_item(runtime, result, s3_ref)

        # Format and return the final execution summary
        return finalize_result(result)

    except Exception as exc:
        logger.exception("Video Lambda setup failed")
        return {"ok": False, "stage": "video", "error": str(exc)}
    finally:

        # Check if runtime exists before attempting cleanup
        if runtime is not None:

            # Close MongoDB connection pool to prevent socket leaks
            runtime.mongo_writer.close()
