"""Environment parsing helpers for channel_lambda."""

from __future__ import annotations

import os


def _required(name: str) -> str:

    # Read the environment variable and remove any leading or trailing whitespace
    value = os.getenv(name, "").strip()

    # Validate that the environment variable is present and not blank
    if not value:

        # Raise an error if a mandatory configuration value is missing
        raise ValueError(f"Missing required environment variable: {name}")

    # Return the cleaned environment variable value
    return value


def _optional(name: str, default: str) -> str:

    # Return the environment variable value if present, otherwise use the default string
    return os.getenv(name, default).strip() or default


def _prefix(name: str, default: str) -> str:

    # Read the environment variable and strip both whitespace and slashes
    value = os.getenv(name, default).strip().strip("/")

    # Return the sanitized prefix or fallback to the default
    return value or default


def _int_env(name: str, default: int, *, minimum: int) -> int:

    # Extract the raw environment variable value and remove whitespace
    raw = os.getenv(name, "").strip()

    # Use the default value if the environment variable is not set
    if not raw:

        # No custom configuration provided
        return default

    # Attempt to convert the raw string to an integer
    try:

        # Parse the string into an integer value
        value = int(raw)

    # Revert to the default value if the string is not a valid integer
    except (ValueError, TypeError):

        # Invalid numeric format encountered
        return default

    # Ensure the returned value meets the specified minimum bound
    return max(value, minimum)
