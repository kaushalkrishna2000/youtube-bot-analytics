"""Serialization helpers for Pydantic models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


def dump_model(model: BaseModel) -> dict[str, Any]:
    """Serialize a Pydantic model and add MongoDB-compatible datetime copies.

    Fields ending in '_at' that contain Zulu timestamps (e.g., '2026-06-03T09:15:00Z')
    will be copied to a new field with the '__d' suffix as a Python datetime object.

    Args:
        model: Pydantic model instance to serialize.

    Returns:
        Dictionary suitable for JSON encoding or Mongo writes.
    """
    # 1. Standard Pydantic serialization
    doc = model.model_dump(mode="json", exclude_none=False)

    # 2. Identify and convert timestamp fields
    timestamp_fields = [k for k in doc.keys() if k.endswith("_at") and isinstance(doc[k], str)]

    for field in timestamp_fields:
        try:
            val = doc[field]
            if val:
                # Replace Zulu 'Z' with '+00:00' for universal ISO compatibility.
                # Python 3.11+ handles 'Z' natively, but this ensures safety across versions.
                clean_val = val.replace("Z", "+00:00")
                doc[f"{field}__d"] = datetime.fromisoformat(clean_val)
        except (ValueError, TypeError):
            # Skip fields that don't match the expected ISO format
            continue

    return doc
