"""Logging configuration for channel_lambda."""

from __future__ import annotations

import logging
import os
import sys


DEFAULT_LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging() -> None:
    """Configure root logging for local runs and AWS Lambda reuse.

    Existing Lambda handlers are updated in place so warm invocations keep the
    current log level without attaching duplicate handlers.
    """
    level = _resolve_log_level(os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL))
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(level)
        for handler in root.handlers:
            handler.setLevel(level)
        return

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    handler.setLevel(level)
    root.addHandler(handler)
    root.setLevel(level)


def _resolve_log_level(raw_level: str) -> int:
    """Convert a string log level to a logging module constant."""
    return getattr(logging, raw_level.strip().upper(), logging.INFO)
