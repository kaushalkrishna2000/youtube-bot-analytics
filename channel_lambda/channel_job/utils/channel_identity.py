"""Channel input normalization and identity parsing."""

from __future__ import annotations

import re
import uuid
from typing import Any
from urllib.parse import urlparse


CHANNEL_ID_RE = re.compile(r"^UC[\w-]{22}$")
HANDLE_RE = re.compile(r"^@([\w.-]+)$", re.IGNORECASE)


def get_job_id(context: Any) -> str:
    return getattr(context, "aws_request_id", None) or uuid.uuid4().hex


def normalize_channel_inputs(values: list[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned:
            continue
        dedupe_key = cleaned.lower()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        normalized.append(cleaned)
    return normalized


def extract_channel_from_url(raw: str) -> str | None:
    parsed = urlparse(raw.strip())
    path = parsed.path.strip("/")
    if not path:
        return None
    parts = path.split("/")
    if parts[0] in ("channel", "c", "user") and len(parts) >= 2:
        return parts[1] if parts[0] == "channel" else f"legacy:{parts[0]}:{parts[1]}"
    if parts[0].startswith("@"):
        return parts[0]
    return None


def parse_int_or_none(value: object) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None
