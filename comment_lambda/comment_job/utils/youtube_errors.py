"""YouTube API error classification helpers."""

from __future__ import annotations

from googleapiclient.errors import HttpError


def is_comments_disabled_error(error: HttpError) -> bool:
    """Return whether a YouTube API error means comments are disabled.

    Args:
        error: Google API HTTP error raised by a comments request.

    Returns:
        ``True`` when the status and reason/body match disabled comments.
    """
    if error.resp.status != 403:
        return False
    try:
        for detail in error.error_details or []:
            if detail.get("reason") in ("commentsDisabled", "disabledComments"):
                return True
    except (AttributeError, TypeError):
        pass
    body = str(error).lower()
    return "commentsdisabled" in body or "disabledcomments" in body
