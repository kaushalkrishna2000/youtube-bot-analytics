"""Comment fetching and commenter enrichment for comment_lambda."""

from __future__ import annotations

from typing import Any

from googleapiclient.errors import HttpError

from comment_job.client.youtube import YouTubeClient
from comment_job.model import CommentDocument
from comment_job.utils.batching import CHANNEL_BATCH_SIZE
from comment_job.utils.comment_parsing import comment_page_size, normalize_author_channel_id
from comment_job.utils.youtube_errors import is_comments_disabled_error


class CommentsDisabledError(ValueError):
    """Raised when YouTube reports disabled comments for a video."""


def fetch_comment_documents(
    client: YouTubeClient,
    *,
    channel_id: str,
    video_id: str,
    max_comments: int,
    delay_ms: int,
) -> tuple[list[CommentDocument], str]:
    comments: list[CommentDocument] = []
    next_page_token: str | None = None
    status = "ok"

    while len(comments) < max_comments:
        try:
            response = _fetch_comment_page(
                client,
                video_id=video_id,
                max_results=comment_page_size(max_comments, len(comments)),
                page_token=next_page_token,
                delay_ms=delay_ms,
            )
        except HttpError as exc:
            if is_comments_disabled_error(exc):
                raise CommentsDisabledError(f"Comments are disabled for video {video_id}") from exc
            if comments:
                status = "partial"
                break
            raise

        items = response.get("items", [])
        for item in items:
            comments.append(_build_comment_document(item, channel_id=channel_id, video_id=video_id))
            if len(comments) >= max_comments:
                break

        next_page_token = response.get("nextPageToken")
        if not next_page_token or not items:
            break

    if not comments and status == "ok":
        status = "none"
    return _enrich_commenter_channels(client, comments, delay_ms=delay_ms), status


def _fetch_comment_page(
    client: YouTubeClient,
    *,
    video_id: str,
    max_results: int,
    page_token: str | None,
    delay_ms: int,
) -> dict[str, Any]:
    request = client.service.commentThreads().list(
        part="snippet",
        videoId=video_id,
        maxResults=max_results,
        textFormat="plainText",
        pageToken=page_token,
    )
    return client.call(request, delay_ms=delay_ms)


def _build_comment_document(item: dict[str, Any], *, channel_id: str, video_id: str) -> CommentDocument:
    top = item.get("snippet", {}).get("topLevelComment", {})
    snippet = top.get("snippet", {})
    author_channel_id = normalize_author_channel_id(snippet.get("authorChannelId"))
    return CommentDocument(
        comment_id=top.get("id", ""),
        channel_id=channel_id,
        video_id=video_id,
        comment_text=snippet.get("textDisplay", ""),
        comment_published_at=snippet.get("publishedAt", ""),
        author_display_name=snippet.get("authorDisplayName", ""),
        author_channel_id=author_channel_id,
        like_count=int(snippet.get("likeCount", 0)),
        enrichment_status="pending" if author_channel_id else "no_channel",
    )


def _enrich_commenter_channels(
    client: YouTubeClient,
    comments: list[CommentDocument],
    *,
    delay_ms: int,
) -> list[CommentDocument]:
    channel_ids = sorted({comment.author_channel_id for comment in comments if comment.author_channel_id})
    if not channel_ids:
        return comments

    channel_map: dict[str, dict[str, Any]] = {}
    for start in range(0, len(channel_ids), CHANNEL_BATCH_SIZE):
        batch = channel_ids[start : start + CHANNEL_BATCH_SIZE]
        request = client.service.channels().list(part="snippet", id=",".join(batch))
        response = client.call(request, delay_ms=delay_ms)
        for item in response.get("items", []):
            author_channel_id = item.get("id")
            if author_channel_id:
                channel_map[author_channel_id] = item.get("snippet", {})

    enriched: list[CommentDocument] = []
    for comment in comments:
        if not comment.author_channel_id:
            enriched.append(comment.model_copy(update={"enrichment_status": "no_channel"}))
            continue
        snippet = channel_map.get(comment.author_channel_id)
        if not snippet:
            enriched.append(comment.model_copy(update={"enrichment_status": "not_found"}))
            continue
        enriched.append(
            comment.model_copy(
                update={
                    "author_channel_title": snippet.get("title"),
                    "author_channel_created_at": snippet.get("publishedAt"),
                    "author_channel_custom_url": snippet.get("customUrl"),
                    "enrichment_status": "ok",
                }
            )
        )
    return enriched
