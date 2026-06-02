"""AWS Lambda entrypoint for scheduled channel staging."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from channel_job.config import configure_logging

# Support both AWS Lambda's flat handler import and package-style local imports.
if __package__:
    from .runner import build_result, finalize_result, load_runtime, process_work_item, resolve_work_items
else:
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
        runtime = load_runtime(event, context)
        result = build_result(runtime)
        for channel_input in resolve_work_items(runtime):
            process_work_item(runtime, result, channel_input)
        return finalize_result(result)
    except Exception as exc:
        logger.exception("Channel Lambda setup failed")
        return {"ok": False, "stage": "channel", "error": str(exc)}
    finally:
        if runtime is not None:
            runtime.mongo_writer.close()
