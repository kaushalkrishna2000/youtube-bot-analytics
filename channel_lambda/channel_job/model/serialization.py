"""Serialization helpers for Pydantic models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


def dump_model(model: BaseModel) -> dict[str, Any]:
    """Serialize a Pydantic model using JSON-compatible values.

    Args:
        model: Pydantic model instance to serialize.

    Returns:
        Dictionary suitable for JSON encoding or Mongo writes.
    """
    return model.model_dump(mode="json", exclude_none=False)
