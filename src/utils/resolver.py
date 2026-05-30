"""
Normalize user channel input to a UC... channel ID.

Resolution order: bare UC id (no API) → @handle → YouTube URL → legacy /c/ or /user/
paths. Raises ChannelNotFoundError when the API returns no matching channel.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

from api.client import YouTubeClient
from models.exceptions import ChannelNotFoundError

logger = logging.getLogger(__name__)

# YouTube channel IDs are 24 chars starting with UC (22 chars after prefix in practice).
CHANNEL_ID_RE = re.compile(r"^UC[\w-]{22}$")
HANDLE_RE = re.compile(r"^@([\w.-]+)$", re.IGNORECASE)

def resolve_channel_id(client: YouTubeClient, channel_input: str) -> str:
    """Resolve a channel URL, @handle, or UC... id to a channel ID."""
    raw = channel_input.strip()

    if CHANNEL_ID_RE.match(raw):
        # Valid canonical ID — skip channels.list to save quota.
        logger.info("Using channel ID directly: %s", raw)
        return raw

    handle_match = HANDLE_RE.match(raw)
    if handle_match:
        logger.info("Resolving @handle: %s", raw)
        channel_id = _resolve_by_handle(client, handle_match.group(1))
        logger.info("Resolved channel_id=%s", channel_id)
        return channel_id

    if raw.startswith("@"):
        logger.info("Resolving @handle: %s", raw)
        channel_id = _resolve_by_handle(client, raw[1:])
        logger.info("Resolved channel_id=%s", channel_id)
        return channel_id

    if "youtube.com" in raw or "youtu.be" in raw:
        logger.info("Parsing channel URL: %s", raw)
        extracted = _extract_from_url(raw)
        if extracted is None:
            raise ChannelNotFoundError(f"Could not parse channel from URL: {raw}")
        if extracted.startswith("@"):
            channel_id = _resolve_by_handle(client, extracted[1:])
            logger.info("Resolved channel_id=%s", channel_id)
            return channel_id
        if extracted.startswith("legacy:"):
            _, kind, name = extracted.split(":", 2)
            logger.info("Resolving legacy path /%s/%s", kind, name)
            channel_id = _resolve_legacy(client, kind, name)
            logger.info("Resolved channel_id=%s", channel_id)
            return channel_id
        if CHANNEL_ID_RE.match(extracted):
            logger.info("Resolved channel_id=%s from URL", extracted)
            return extracted
        raise ChannelNotFoundError(f"Unrecognized channel URL format: {raw}")

    logger.info("Resolving bare handle/name: %s", raw)
    channel_id = _resolve_by_handle(client, raw)
    logger.info("Resolved channel_id=%s", channel_id)
    return channel_id


def _resolve_by_handle(client: YouTubeClient, handle: str) -> str:
    # Step 1: build request. Step 2: client.call() runs .execute() on the network.
    request = client.service.channels().list(part="id", forHandle=handle)
    response = client.call(request)
    items = response.get("items", [])
    if items:
        return items[0]["id"]
    raise ChannelNotFoundError(f"Channel not found for handle: @{handle}")


def _resolve_legacy(client: YouTubeClient, kind: str, name: str) -> str:
    # Pre-handle era: /user/USERNAME uses forUsername; /c/ often maps to a custom slug.
    if kind == "user":
        request = client.service.channels().list(part="id", forUsername=name)
    else:
        request = client.service.channels().list(part="id", forHandle=name)
    response = client.call(request)
    items = response.get("items", [])
    if items:
        return items[0]["id"]
    raise ChannelNotFoundError(f"Channel not found for legacy path /{kind}/{name}")


def _extract_from_url(raw: str) -> str | None:
    """Return channel id or handle token from a YouTube URL."""
    parsed = urlparse(raw.strip())
    path = parsed.path.strip("/")

    if not path:
        return None

    parts = path.split("/")
    # /channel/UC... returns id directly; /c/name and /user/name need a follow-up API call.
    if parts[0] in ("channel", "c", "user") and len(parts) >= 2:
        return parts[1] if parts[0] == "channel" else f"legacy:{parts[0]}:{parts[1]}"

    if parts[0].startswith("@"):
        return parts[0]

    return None