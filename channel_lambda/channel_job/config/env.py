"""Environment parsing helpers for channel_lambda."""

from __future__ import annotations

import os


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _optional(name: str, default: str) -> str:
    return os.getenv(name, default).strip() or default


def _prefix(name: str, default: str) -> str:
    value = os.getenv(name, default).strip().strip("/")
    return value or default


def _int_env(name: str, default: int, *, minimum: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(value, minimum)
