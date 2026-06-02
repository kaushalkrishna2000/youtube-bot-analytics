"""Small normalization helpers shared across Lambda, runner, and services.

The helpers here keep boundary cleanup consistent: environment lists are trimmed,
numeric options are coerced with minimums, and YouTube response quirks are
normalized before they reach the domain models.
"""

from __future__ import annotations

from typing import Any

from googleapiclient.errors import HttpError


def parse_int_or_none(value: str | None) -> int | None:
    """Parse a YouTube numeric string, returning ``None`` for missing/bad data."""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def normalize_nonempty_str_list(values: list[object]) -> list[str]:
    """Keep only non-empty strings from a mixed input list."""
    cleaned: list[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        stripped = value.strip()
        if stripped:
            cleaned.append(stripped)
    return cleaned


def coerce_int_with_min(value: Any, *, field_name: str, minimum: int = 1) -> tuple[int | None, str | None]:
    """Coerce a value to ``int`` and clamp it to a minimum.

    Returns:
        ``(number, None)`` on success, or ``(None, error_message)`` when the
        value cannot be parsed as an integer.
    """
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None, f"{field_name} must be an integer"
    if number < minimum:
        return minimum, None
    return number, None


def normalize_author_channel_id(raw: object) -> str | None:
    """Normalize YouTube's authorChannelId field to a plain string or ``None``.

    The API may return the field as a string or as ``{"value": "UC..."}``
    depending on endpoint/client behavior.
    """
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
    """Return whether a YouTube ``HttpError`` represents disabled comments."""
    if error.resp.status != 403:
        return False
    try:
        # googleapiclient may expose parsed detail records with a reason code.
        for detail in error.error_details or []:
            reason = detail.get("reason", "")
            if reason in ("commentsDisabled", "disabledComments"):
                return True
    except (AttributeError, TypeError):
        pass
    # Fall back to the rendered error text because some client versions do not populate error_details consistently.
    body = str(error).lower()
    return "commentsdisabled" in body or "disabledcomments" in body
