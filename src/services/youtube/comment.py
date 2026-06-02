"""Comment fetch and commenter-channel enrichment service calls.

The report layer asks this module for top-level comments on one video and then
for author channel metadata. Known YouTube states such as disabled comments and
partial pagination failures are translated into domain statuses so the Lambda
can keep returning useful partial results.
"""

from __future__ import annotations

import logging

from googleapiclient.errors import HttpError

from core.youtube_client import YouTubeClient
from core.config import CHANNELS_BATCH_SIZE
from core.exceptions import CommentsDisabledError
from domain.models import CommentRecord
from utils.basic_utils import is_comments_disabled_error, normalize_author_channel_id

logger = logging.getLogger(__name__)


def fetch_top_level_comments(client: YouTubeClient, video_id: str, *, max_comments: int = 1000, delay_ms: int = 0) -> tuple[list[CommentRecord], str]:
    """Fetch top-level comments for a video.

    Returns:
        ``(comments, status)`` where status is ``"ok"``, ``"none"``, or
        ``"partial"``. Disabled comments raise ``CommentsDisabledError`` so
        ``logic.fetcher`` can mark the video with ``comments_status="disabled"``.
    """
    limit = max(max_comments, 1)
    logger.info("Fetching up to %s top-level comments for video %s", limit, video_id)
    records: list[CommentRecord] = []
    next_page_token: str | None = None
    status = "ok"

    while len(records) < limit:
        # commentThreads.list allows up to 100 results per request. Keep paging until the caller's limit, the API's final page, or a partial failure.
        page_size = min(100, limit - len(records))
        try:
            threads_request = client.service.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=page_size,
                textFormat="plainText",
                pageToken=next_page_token,
            )
            response = client.call(threads_request, delay_ms=delay_ms)
        except HttpError as exc:
            if is_comments_disabled_error(exc):
                raise CommentsDisabledError(f"Comments are disabled for video {video_id}") from exc
            if records:
                # If earlier pages succeeded, keep the usable comments and let the report surface this as a partial video-level result.
                logger.warning("Partial comments fetch for video %s due to API error", video_id)
                status = "partial"
                break
            raise

        items = response.get("items", [])
        for item in items:
            top = item.get("snippet", {}).get("topLevelComment", {})
            top_snippet = top.get("snippet", {})
            author_channel_id = normalize_author_channel_id(top_snippet.get("authorChannelId"))
            # YouTube may omit authorChannelId for deleted/private authors. The enrichment step can skip those cleanly when marked no_channel.
            records.append(
                CommentRecord(
                    comment_id=top.get("id", ""),
                    comment_text=top_snippet.get("textDisplay", ""),
                    comment_published_at=top_snippet.get("publishedAt", ""),
                    author_display_name=top_snippet.get("authorDisplayName", ""),
                    author_channel_id=author_channel_id,
                    like_count=int(top_snippet.get("likeCount", 0)),
                    enrichment_status="no_channel" if not author_channel_id else "pending",
                )
            )
            if len(records) >= limit:
                break
        logger.info(
            "Fetched comments page: %s item(s) (total=%s/%s)",
            len(items),
            len(records),
            limit,
        )

        next_page_token = response.get("nextPageToken")
        if not next_page_token or not items:
            break

    if not records and status == "ok":
        status = "none"
    logger.info("Comments fetch finished for %s: count=%s status=%s", video_id, len(records), status)
    return records, status


def enrich_commenter_channels(client: YouTubeClient, comments: list[CommentRecord], *, delay_ms: int = 0) -> list[CommentRecord]:
    """Enrich comments with available author channel metadata.

    The function mutates and returns the same ``CommentRecord`` objects. Missing
    channel IDs become ``no_channel``; IDs not returned by ``channels.list`` are
    marked ``not_found``; successful matches receive title, published date, and
    custom URL fields.
    """
    unique_ids = {c.author_channel_id for c in comments if c.author_channel_id}
    if not unique_ids:
        logger.info("No commenter channel IDs to enrich")
        return comments

    channel_map: dict[str, dict] = {}
    id_list = list(unique_ids)
    logger.info("Enriching %s unique commenter channel(s)", len(id_list))

    for start in range(0, len(id_list), CHANNELS_BATCH_SIZE):
        # channels.list accepts at most 50 IDs per request, so enrichment is chunked independently of comment pagination.
        batch = id_list[start : start + CHANNELS_BATCH_SIZE]
        logger.info("Enrichment batch size: %s", len(batch))
        enrich_request = client.service.channels().list(part="snippet", id=",".join(batch))
        response = client.call(enrich_request, delay_ms=delay_ms)
        for item in response.get("items", []):
            channel_map[item["id"]] = item.get("snippet", {})

    for comment in comments:
        # author_channel_id was already normalized when the record was built.
        channel_id = comment.author_channel_id
        if not channel_id:
            comment.enrichment_status = "no_channel"
            continue

        snippet = channel_map.get(channel_id)
        if not snippet:
            comment.enrichment_status = "not_found"
            continue

        comment.author_channel_title = snippet.get("title")
        comment.author_channel_created_at = snippet.get("publishedAt")
        comment.author_channel_custom_url = snippet.get("customUrl")
        comment.enrichment_status = "ok"

    logger.info("Commenter enrichment complete for %s comment(s)", len(comments))
    return comments
