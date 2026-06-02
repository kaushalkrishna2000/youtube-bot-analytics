"""Environment parsing helpers for video_lambda."""

from __future__ import annotations

import os


def _required(name: str) -> str:
    """Read and validate a required environment variable.

    Args:
        name: Environment variable name.

    Returns:
        Trimmed environment value.

    Raises:
        ValueError: If the environment variable is missing or blank.
    """
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _optional(name: str, default: str) -> str:
    """Read an optional environment variable with a string default."""
    return os.getenv(name, default).strip() or default


def _prefix(name: str, default: str) -> str:
    """Read an S3 prefix environment variable without leading/trailing slashes."""
    value = os.getenv(name, default).strip().strip("/")
    return value or default


def _int_env(name: str, default: int, *, minimum: int) -> int:
    """Read an integer environment variable with fallback and minimum bounds."""
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(value, minimum)
