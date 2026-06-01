"""Configure root logger to stderr for Lambda/runtime flows."""

from __future__ import annotations

import logging
import sys

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging(*, level: int, quiet: bool) -> None:
    """Configure root logging to stderr. Idempotent if handlers already exist."""
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
