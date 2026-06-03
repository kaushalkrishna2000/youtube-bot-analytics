"""S3 event parsing for video_lambda."""

from __future__ import annotations

from typing import Any
from urllib.parse import unquote_plus


def parse_s3_event(event: dict[str, Any] | None) -> list[dict[str, str]]:

    # Validate that the incoming event is a dictionary
    if not isinstance(event, dict):

        # Raise an error for invalid event types
        raise ValueError("S3 event must be a dictionary")

    # Extract the Records list from the event dictionary
    records = event.get("Records")

    # Validate that Records is a non-empty list
    if not isinstance(records, list) or not records:

        # Raise an error if no records are found in the event
        raise ValueError("S3 event does not contain Records")

    # Initialize a list to hold the parsed bucket and key references
    refs: list[dict[str, str]] = []

    # Iterate through each record in the event
    for record in records:

        # Safely extract the S3 information dictionary from the record
        s3_info = record.get("s3", {}) if isinstance(record, dict) else {}

        # Retrieve the bucket name and object key from the S3 info
        bucket = s3_info.get("bucket", {}).get("name")

        key = s3_info.get("object", {}).get("key")

        # Validate that both bucket and key are present
        if not bucket or not key:

            # Raise an error if record metadata is incomplete
            raise ValueError("S3 event record missing bucket or key")

        # Decode the URL-encoded key and append to the result list
        refs.append({"bucket": bucket, "key": unquote_plus(key)})

    # Return the collected list of S3 object references
    return refs
