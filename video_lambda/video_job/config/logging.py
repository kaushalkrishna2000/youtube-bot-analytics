"""Logging configuration for video_lambda."""

from __future__ import annotations

import logging
import os
import sys


DEFAULT_LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging() -> None:

    # Determine the desired log level from environment variables or use the default
    level = _resolve_log_level(os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL))

    # Retrieve the root logger instance
    root = logging.getLogger()

    # Update existing handlers if they are already attached to the root logger
    if root.handlers:

        # Apply the new log level to the root logger
        root.setLevel(level)

        # Update each individual handler with the new log level
        for handler in root.handlers:
            handler.setLevel(level)

        # Exit early since handlers are already configured
        return

    # Create a new stream handler for standard error output
    handler = logging.StreamHandler(sys.stderr)

    # Set the log message format and date format for the handler
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

    # Apply the log level to the newly created handler
    handler.setLevel(level)

    # Add the handler to the root logger
    root.addHandler(handler)

    # Apply the log level to the root logger
    root.setLevel(level)


def _resolve_log_level(raw_level: str) -> int:

    # Return the logging constant matching the trimmed uppercase input string
    return getattr(logging, raw_level.strip().upper(), logging.INFO)
