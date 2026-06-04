"""Comment parsing helpers."""

from __future__ import annotations


COMMENT_PAGE_SIZE = 100


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------


def normalize_author_channel_id(raw: object) -> str | None:

    # Return None if the raw input is missing
    if raw is None:

        # No author channel information provided
        return None

    # Handle cases where the author channel ID is provided as a direct string
    if isinstance(raw, str):

        # Return the trimmed string or None if empty
        return raw.strip() or None

    # Handle cases where the ID is nested within a dictionary
    if isinstance(raw, dict):

        # Extract the value field from the dictionary
        value = raw.get("value")

        # Return the trimmed value if it is a string
        if isinstance(value, str):

            # Return the sanitized string or None if empty
            return value.strip() or None

    # Return None if the input shape was not recognized
    return None


def comment_page_size(max_comments: int, current_count: int) -> int:

    # Calculate the remaining capacity and return the smaller of page size or capacity
    return min(COMMENT_PAGE_SIZE, max_comments - current_count)
