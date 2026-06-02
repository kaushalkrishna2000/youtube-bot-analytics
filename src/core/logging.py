"""Root logging setup for Lambda and local runner flows.

The fetch job emits INFO-level progress logs by default so Lambda operators can
follow validation, API progress, S3 upload, and response decisions in
CloudWatch. ``quiet=True`` keeps errors visible while suppressing normal flow
logs for local or automated callers.
"""

from __future__ import annotations

import logging
import sys

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging(*, level: int, quiet: bool) -> None:
    """Configure root logging to stderr.

    The function is idempotent because AWS Lambda may reuse the Python process
    across invocations. Existing handlers keep their formatter, while the root
    level is still updated for the current run.
    """
    # --quiet hides INFO flow logs but still allows ERROR from failed API/config.
    effective_level = logging.ERROR if quiet else level
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(effective_level)
        return

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
    root.addHandler(handler)
    root.setLevel(effective_level)
