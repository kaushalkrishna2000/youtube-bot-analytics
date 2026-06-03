"""Channel resolution and metadata fetching for channel_lambda."""

from __future__ import annotations

from channel_job.client.youtube import YouTubeClient
from channel_job.model import ChannelDocument
from channel_job.utils.channel_identity import CHANNEL_ID_RE, HANDLE_RE, extract_channel_from_url, parse_int_or_none


class ChannelNotFoundError(ValueError):
    """Raised when a channel input cannot be resolved to a YouTube channel."""


def fetch_channel_document(client: YouTubeClient, channel_input: str, *, delay_ms: int) -> ChannelDocument:

    # Resolve the provided input string into a canonical YouTube channel ID
    channel_id = resolve_channel_id(client, channel_input, delay_ms=delay_ms)

    # Prepare the YouTube API request for channel snippets and statistics
    request = client.service.channels().list(part="snippet,statistics", id=channel_id)

    # Execute the API call with optional throttling delay
    response = client.call(request, delay_ms=delay_ms)

    # Extract the list of channel items from the response
    items = response.get("items", [])

    # Raise an error if no channel items were returned for the ID
    if not items:

        # Indicate that the specific channel could not be found
        raise ChannelNotFoundError(f"Channel not found: {channel_id}")

    # Process the first matching channel item
    item = items[0]

    # Extract snippet and statistics dictionaries from the item
    snippet = item.get("snippet", {})

    stats = item.get("statistics", {})

    # Return a validated ChannelDocument populated with metadata
    return ChannelDocument(
        input_raw=channel_input,
        channel_id=channel_id,
        title=snippet.get("title"),
        custom_url=snippet.get("customUrl"),
        channel_created_at=snippet.get("publishedAt"),
        subscriber_count=parse_int_or_none(stats.get("subscriberCount")),
        video_count=parse_int_or_none(stats.get("videoCount")),
    )


def resolve_channel_id(client: YouTubeClient, channel_input: str, *, delay_ms: int) -> str:

    # Clean the input string and check for a direct channel ID match
    raw = channel_input.strip()

    if CHANNEL_ID_RE.match(raw):

        # Return the input if it is already a canonical channel ID
        return raw

    # Check if the input is a handle starting with @
    handle_match = HANDLE_RE.match(raw)

    if handle_match:

        # Resolve the handle to a channel ID via API lookup
        return _resolve_by_handle(client, handle_match.group(1), delay_ms=delay_ms)

    # Handle cases where @ is provided but not matched by the regex
    if raw.startswith("@"):

        # Attempt to resolve the handle without the @ prefix
        return _resolve_by_handle(client, raw[1:], delay_ms=delay_ms)

    # Detect if the input is a YouTube URL
    if "youtube.com" in raw or "youtu.be" in raw:

        # Extract the channel token from the URL structure
        extracted = extract_channel_from_url(raw)

        # Raise an error if no identifier could be extracted from the URL
        if extracted is None:

            # Indicate that the URL format was not recognized
            raise ChannelNotFoundError(f"Could not parse channel from URL: {raw}")

        # Handle @handle tokens extracted from URLs
        if extracted.startswith("@"):

            # Resolve the extracted handle to a channel ID
            return _resolve_by_handle(client, extracted[1:], delay_ms=delay_ms)

        # Handle legacy tokens (user or c) extracted from URLs
        if extracted.startswith("legacy:"):

            # Split the legacy marker into kind and identifier name
            _, kind, name = extracted.split(":", 2)

            # Resolve the legacy path to a canonical channel ID
            return _resolve_legacy(client, kind, name, delay_ms=delay_ms)

        # Return the extracted token if it matches the channel ID pattern
        if CHANNEL_ID_RE.match(extracted):

            # Use the extracted channel ID directly
            return extracted

        # Raise an error for unrecognized URL tokens
        raise ChannelNotFoundError(f"Unrecognized channel URL format: {raw}")

    # Fall back to resolving the input as a handle if no other pattern matched
    return _resolve_by_handle(client, raw, delay_ms=delay_ms)


def _resolve_by_handle(client: YouTubeClient, handle: str, *, delay_ms: int) -> str:

    # Prepare a request to list channel IDs matching the given handle
    request = client.service.channels().list(part="id", forHandle=handle)

    # Execute the API call to resolve the handle
    response = client.call(request, delay_ms=delay_ms)

    # Extract the list of matching channel items
    items = response.get("items", [])

    # Return the ID of the first matching channel
    if items:

        # Successfully resolved the handle to an ID
        return items[0]["id"]

    # Raise an error if no channel was found for the handle
    raise ChannelNotFoundError(f"Channel not found for handle: @{handle}")


def _resolve_legacy(client: YouTubeClient, kind: str, name: str, *, delay_ms: int) -> str:

    # Determine whether to search by username or handle based on legacy kind
    if kind == "user":

        # Use the forUsername filter for legacy user paths
        request = client.service.channels().list(part="id", forUsername=name)

    else:

        # Use the forHandle filter for legacy c paths
        request = client.service.channels().list(part="id", forHandle=name)

    # Execute the API call to resolve the legacy path
    response = client.call(request, delay_ms=delay_ms)

    # Extract the list of matching channel items
    items = response.get("items", [])

    # Return the ID of the first matching channel
    if items:

        # Successfully resolved the legacy path to an ID
        return items[0]["id"]

    # Raise an error if the legacy path could not be resolved
    raise ChannelNotFoundError(f"Channel not found for legacy path /{kind}/{name}")
