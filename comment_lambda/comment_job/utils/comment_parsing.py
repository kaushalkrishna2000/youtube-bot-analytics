"""Comment parsing helpers."""

from __future__ import annotations


COMMENT_PAGE_SIZE = 100


def normalize_author_channel_id(raw: object) -> str | None:
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
    return min(COMMENT_PAGE_SIZE, max_comments - current_count)
