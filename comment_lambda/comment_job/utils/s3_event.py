"""S3 event parsing for comment_lambda."""

from __future__ import annotations

from typing import Any
from urllib.parse import unquote_plus


def parse_s3_event(event: dict[str, Any] | None) -> list[dict[str, str]]:
    """Extract bucket/key references from an AWS S3 notification event.

    Args:
        event: Raw Lambda event payload.

    Returns:
        List of dictionaries with decoded ``bucket`` and ``key`` values.

    Raises:
        ValueError: If the event is missing S3 records or object references.
    """
    if not isinstance(event, dict):
        raise ValueError("S3 event must be a dictionary")
    records = event.get("Records")
    if not isinstance(records, list) or not records:
        raise ValueError("S3 event does not contain Records")

    refs: list[dict[str, str]] = []
    for record in records:
        s3_info = record.get("s3", {}) if isinstance(record, dict) else {}
        bucket = s3_info.get("bucket", {}).get("name")
        key = s3_info.get("object", {}).get("key")
        if not bucket or not key:
            raise ValueError("S3 event record missing bucket or key")
        # S3 notifications URL-encode keys, including spaces as plus signs.
        refs.append({"bucket": bucket, "key": unquote_plus(key)})
    return refs
