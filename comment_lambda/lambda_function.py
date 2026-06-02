"""AWS Lambda entrypoint for S3-triggered comment staging."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comment_job.config import configure_logging

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
    """Run the S3-triggered comment staging Lambda.

    Args:
        event: S3 event payload containing video-stage objects to process.
        context: AWS Lambda context object. It is accepted for AWS compatibility
            and local runner symmetry.

    Returns:
        Result dictionary containing processed inputs, staged comment outputs,
        Mongo update counts, and any per-object errors.
    """
    runtime = None
    try:
        runtime = load_runtime(event, context)
        result = build_result(runtime)
        for s3_ref in resolve_work_items(runtime):
            process_work_item(runtime, result, s3_ref)
        return finalize_result(result)
    except Exception as exc:
        logger.exception("Comment Lambda setup failed")
        return {"ok": False, "stage": "comment", "error": str(exc)}
    finally:
        if runtime is not None:
            runtime.mongo_writer.close()
