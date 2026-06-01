"""Shared basic utilities used across Lambda/services."""

from __future__ import annotations

from typing import Any

from googleapiclient.errors import HttpError


def parse_int_or_none(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def normalize_nonempty_str_list(values: list[object]) -> list[str]:
    cleaned: list[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        stripped = value.strip()
        if stripped:
            cleaned.append(stripped)
    return cleaned


def coerce_int_with_min(value: Any, *, field_name: str, minimum: int = 1) -> tuple[int | None, str | None]:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None, f"{field_name} must be an integer"
    if number < minimum:
        return minimum, None
    return number, None


def normalize_author_channel_id(raw: object) -> str | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        stripped = raw.strip()
        return stripped or None
    if isinstance(raw, dict):
        value = raw.get("value")
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
    return None


def is_comments_disabled_error(error: HttpError) -> bool:
    if error.resp.status != 403:
        return False
    try:
        for detail in error.error_details or []:
            reason = detail.get("reason", "")
            if reason in ("commentsDisabled", "disabledComments"):
                return True
    except (AttributeError, TypeError):
        pass
    body = str(error).lower()
    return "commentsdisabled" in body or "disabledcomments" in body
