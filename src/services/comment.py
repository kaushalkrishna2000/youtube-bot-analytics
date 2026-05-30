"""
Top-level comment threads and batched commenter channel enrichment.

commentThreads.list returns only top-level comments (not replies). Enrichment
deduplicates author_channel_id values then calls channels.list in batches of 50.
"""

from __future__ import annotations

import logging

from googleapiclient.errors import HttpError

from api.client import YouTubeClient
from core.config import CHANNELS_BATCH_SIZE, MAX_COMMENTS_CAP
from models.exceptions import CommentsDisabledError
from models.records import CommentRecord

logger = logging.getLogger(__name__)


def fetch_top_level_comments(client: YouTubeClient, video_id: str, *, max_comments: int = 100, delay_ms: int = 0) -> list[CommentRecord]:
    """Fetch top-level comment threads and map each thread into CommentRecord."""
    limit = min(max(max_comments, 1), MAX_COMMENTS_CAP)
    logger.info("Fetching up to %s top-level comments for video %s", limit, video_id)

    try:
        threads_request = client.service.commentThreads().list(part="snippet",videoId=video_id,maxResults=limit,textFormat="plainText")
        response = client.call(threads_request, delay_ms=delay_ms)
    except HttpError as exc:
        if _is_comments_disabled(exc):
            raise CommentsDisabledError(f"Comments are disabled for video {video_id}") from exc
        raise

    records: list[CommentRecord] = []
    for item in response.get("items", []):
        # topLevelComment.snippet holds the flat fields used by comments.csv.
        top = item.get("snippet", {}).get("topLevelComment", {})
        top_snippet = top.get("snippet", {})
        author_channel_id = _normalize_author_channel_id(top_snippet.get("authorChannelId"))
        # pending means "look up this author later"; no_channel has nothing to enrich.
        record = CommentRecord(
            comment_id=top.get("id", ""),
            comment_text=top_snippet.get("textDisplay", ""),
            comment_published_at=top_snippet.get("publishedAt", ""),
            author_display_name=top_snippet.get("authorDisplayName", ""),
            author_channel_id=author_channel_id,
            like_count=int(top_snippet.get("likeCount", 0)),
            enrichment_status="no_channel" if not author_channel_id else "pending",
        )
        records.append(record)
    logger.info("Fetched %s comment(s)", len(records))
    logger.debug("commentThreads.list returned %s item(s)", len(response.get("items", [])))
    return records


def enrich_commenter_channels(client: YouTubeClient, comments: list[CommentRecord], *, delay_ms: int = 0) -> list[CommentRecord]:
    """Batch-fetch channel metadata for unique commenter channel IDs."""
    # Deduplicate before channels.list so repeated commenters cost one lookup.
    unique_ids = {c.author_channel_id for c in comments if c.author_channel_id}
    if not unique_ids:
        logger.info("No commenter channel IDs to enrich")
        return comments

    channel_map: dict[str, dict] = {}
    id_list = list(unique_ids)
    batch_count = (len(id_list) + CHANNELS_BATCH_SIZE - 1) // CHANNELS_BATCH_SIZE
    logger.info("Enriching %s unique commenter channel(s) (%s batch(es))", len(id_list), batch_count)

    for start in range(0, len(id_list), CHANNELS_BATCH_SIZE):
        batch = id_list[start : start + CHANNELS_BATCH_SIZE]
        ids_param = ",".join(batch)
        batch_num = start // CHANNELS_BATCH_SIZE + 1
        logger.debug("Enrichment batch %s/%s (%s channel(s))", batch_num, batch_count, len(batch))
        # id= accepts up to 50 comma-separated channel IDs per channels.list call.
        enrich_request = client.service.channels().list(part="snippet", id=ids_param)
        response = client.call(enrich_request, delay_ms=delay_ms)
        items = response.get("items", [])
        logger.debug("channels.list returned %s item(s)", len(items))
        for item in items:
            # Store snippets by channel ID so we can map enrichment back to comments.
            channel_map[item["id"]] = item.get("snippet", {})

    for comment in comments:
        channel_id = _normalize_author_channel_id(comment.author_channel_id)
        comment.author_channel_id = channel_id
        if not channel_id:
            comment.enrichment_status = "no_channel"
            continue

        snippet = channel_map.get(channel_id)
        if not snippet:
            comment.enrichment_status = "not_found"
            continue

        # Enriched author fields support bot-review filters in JSON/CSV exports.
        comment.author_channel_title = snippet.get("title")
        comment.author_channel_created_at = snippet.get("publishedAt")
        comment.author_channel_custom_url = snippet.get("customUrl")
        comment.enrichment_status = "ok"

    return comments


def _normalize_author_channel_id(raw: object) -> str | None:
    """Normalize authorChannelId from either a string or {\"value\": \"UC...\"}."""
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


def _is_comments_disabled(error: HttpError) -> bool:
    """YouTube returns 403 with reason commentsDisabled when threads are turned off."""
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
