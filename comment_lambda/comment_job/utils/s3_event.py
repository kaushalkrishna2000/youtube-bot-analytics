"""S3 event parsing for comment_lambda."""

from __future__ import annotations

from typing import Any
from urllib.parse import unquote_plus


def parse_s3_event(event: dict[str, Any] | None) -> list[dict[str, str]]:
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
        refs.append({"bucket": bucket, "key": unquote_plus(key)})
    return refs
