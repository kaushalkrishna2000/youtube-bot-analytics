"""Text helpers for video_lambda."""

from __future__ import annotations

import re


def slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.=-]+", "-", value).strip("-") or "unknown"
