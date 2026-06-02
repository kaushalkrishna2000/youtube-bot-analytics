"""Channel resolution and metadata fetching for channel_lambda."""

from __future__ import annotations

from channel_job.client.youtube import YouTubeClient
from channel_job.model import ChannelDocument
from channel_job.utils.channel_identity import CHANNEL_ID_RE, HANDLE_RE, extract_channel_from_url, parse_int_or_none


class ChannelNotFoundError(ValueError):
    """Raised when a channel input cannot be resolved to a YouTube channel."""


def fetch_channel_document(client: YouTubeClient, channel_input: str, *, delay_ms: int) -> ChannelDocument:
    channel_id = resolve_channel_id(client, channel_input, delay_ms=delay_ms)
    request = client.service.channels().list(part="snippet,statistics", id=channel_id)
    response = client.call(request, delay_ms=delay_ms)
    items = response.get("items", [])
    if not items:
        raise ChannelNotFoundError(f"Channel not found: {channel_id}")

    item = items[0]
    snippet = item.get("snippet", {})
    stats = item.get("statistics", {})
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
    raw = channel_input.strip()
    if CHANNEL_ID_RE.match(raw):
        return raw

    handle_match = HANDLE_RE.match(raw)
    if handle_match:
        return _resolve_by_handle(client, handle_match.group(1), delay_ms=delay_ms)

    if raw.startswith("@"):
        return _resolve_by_handle(client, raw[1:], delay_ms=delay_ms)

    if "youtube.com" in raw or "youtu.be" in raw:
        extracted = extract_channel_from_url(raw)
        if extracted is None:
            raise ChannelNotFoundError(f"Could not parse channel from URL: {raw}")
        if extracted.startswith("@"):
            return _resolve_by_handle(client, extracted[1:], delay_ms=delay_ms)
        if extracted.startswith("legacy:"):
            _, kind, name = extracted.split(":", 2)
            return _resolve_legacy(client, kind, name, delay_ms=delay_ms)
        if CHANNEL_ID_RE.match(extracted):
            return extracted
        raise ChannelNotFoundError(f"Unrecognized channel URL format: {raw}")

    return _resolve_by_handle(client, raw, delay_ms=delay_ms)


def _resolve_by_handle(client: YouTubeClient, handle: str, *, delay_ms: int) -> str:
    request = client.service.channels().list(part="id", forHandle=handle)
    response = client.call(request, delay_ms=delay_ms)
    items = response.get("items", [])
    if items:
        return items[0]["id"]
    raise ChannelNotFoundError(f"Channel not found for handle: @{handle}")


def _resolve_legacy(client: YouTubeClient, kind: str, name: str, *, delay_ms: int) -> str:
    if kind == "user":
        request = client.service.channels().list(part="id", forUsername=name)
    else:
        request = client.service.channels().list(part="id", forHandle=name)
    response = client.call(request, delay_ms=delay_ms)
    items = response.get("items", [])
    if items:
        return items[0]["id"]
    raise ChannelNotFoundError(f"Channel not found for legacy path /{kind}/{name}")
