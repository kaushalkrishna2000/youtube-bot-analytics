"""Text helpers for comment_lambda."""

from __future__ import annotations

import re


def slug(value: str) -> str:
    """Convert a value into a safe S3 key segment."""
    return re.sub(r"[^A-Za-z0-9_.=-]+", "-", value).strip("-") or "unknown"
