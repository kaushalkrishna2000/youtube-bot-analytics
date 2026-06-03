"""Batching helpers for video_lambda."""

from __future__ import annotations

from typing import TypeVar


VIDEO_BATCH_SIZE = 50

T = TypeVar("T")


def iter_batches(values: list[T], batch_size: int) -> list[list[T]]:

    # Generate a list of fixed-size sub-lists from the original input
    return [values[start : start + batch_size] for start in range(0, len(values), batch_size)]
