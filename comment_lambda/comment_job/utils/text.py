"""Text helpers for comment_lambda."""

from __future__ import annotations

import re


def slug(value: str) -> str:

    # Replace any non-alphanumeric characters with hyphens and strip excess hyphens
    return re.sub(r"[^A-Za-z0-9_.=-]+", "-", value).strip("-") or "unknown"
