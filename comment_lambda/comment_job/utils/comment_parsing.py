"""Comment parsing helpers."""

from __future__ import annotations


COMMENT_PAGE_SIZE = 100


def normalize_author_channel_id(raw: object) -> str | None:
    """Normalize YouTube's author channel ID shape to a plain string.

    Args:
        raw: Value from ``authorChannelId``. YouTube can return either a string
            or a dictionary containing ``value``.

    Returns:
        Trimmed author channel ID, or ``None`` when unavailable.
    """
    if raw is None:
        return None
    if isinstance(raw, str):
        return raw.strip() or None
    if isinstance(raw, dict):
        value = raw.get("value")
        if isinstance(value, str):
            return value.strip() or None
    return None


def comment_page_size(max_comments: int, current_count: int) -> int:
    """Calculate the next comment page size without exceeding the configured cap."""
    return min(COMMENT_PAGE_SIZE, max_comments - current_count)
