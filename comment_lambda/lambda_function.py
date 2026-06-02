"""AWS Lambda entrypoint for S3-triggered comment staging."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comment_job.config import configure_logging

if __package__:
    from .runner import build_result, finalize_result, load_runtime, process_work_item, resolve_work_items
else:
    from runner import build_result, finalize_result, load_runtime, process_work_item, resolve_work_items

configure_logging()
logger = logging.getLogger(__name__)


def lambda_handler(event: dict[str, Any] | None, context: Any) -> dict[str, Any]:
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
