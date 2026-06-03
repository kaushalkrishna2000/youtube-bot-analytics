"""AWS Lambda entrypoint for scheduled channel staging."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

# Add local directory to path for module discovery in AWS
sys.path.insert(0, str(Path(__file__).resolve().parent))

from channel_job.config import configure_logging

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
    """Run the scheduled channel staging Lambda.

    Args:
        event: EventBridge payload or a local test event. The channel stage reads
            channel inputs from configuration instead of from the event body.
        context: AWS Lambda context object used to derive the job identifier.

    Returns:
        Result dictionary containing stage counts, S3 outputs, and any per-item
        errors collected during the run.
    """
    runtime = None
    try:

        # Prepare dependencies and configuration
        runtime = load_runtime(event, context)

        # Initialize the result dictionary for tracking progress
        result = build_result(runtime)

        # Loop through each work item identified from the event
        for channel_input in resolve_work_items(runtime):

            # Execute the core logic for each individual item
            process_work_item(runtime, result, channel_input)

        # Format and return the final execution summary
        return finalize_result(result)

    except Exception as exc:
        logger.exception("Channel Lambda setup failed")
        return {"ok": False, "stage": "channel", "error": str(exc)}
    finally:

        # Check if runtime exists before attempting cleanup
        if runtime is not None:

            # Close MongoDB connection pool to prevent socket leaks
            runtime.mongo_writer.close()
