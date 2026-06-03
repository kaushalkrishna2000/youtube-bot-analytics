"""YouTube API error classification helpers."""

from __future__ import annotations

from googleapiclient.errors import HttpError


def is_comments_disabled_error(error: HttpError) -> bool:

    # Check if the error status is 403 Forbidden
    if error.resp.status != 403:

        # Not a permission-related error
        return False

    # Inspect the error details for specific reason codes
    try:

        # Iterate through any detailed error reasons provided by the API
        for detail in error.error_details or []:

            # Check for known reasons indicating disabled comments
            if detail.get("reason") in ("commentsDisabled", "disabledComments"):

                # Confirmed disabled comments
                return True

    # Handle cases where error details are missing or malformed
    except (AttributeError, TypeError):

        # Proceed to string matching if structured details are unavailable
        pass

    # Fall back to matching the error message string
    body = str(error).lower()

    # Return True if any disabled comments keywords are present in the body
    return "commentsdisabled" in body or "disabledcomments" in body
