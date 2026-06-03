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

    # Initialize a list to hold the collected comment documents
    comments: list[CommentDocument] = []

    # Track the token for the next page of comments
    next_page_token: str | None = None

    # Track the overall fetch status of the operation
    status = "ok"

    # Continue fetching until the requested count is reached
    while len(comments) < max_comments:

        # Attempt to fetch a single page of comments from the API
        try:

            # Retrieve a batch of comments matching the video ID
            response = _fetch_comment_page(
                client,
                video_id=video_id,
                max_results=comment_page_size(max_comments, len(comments)),
                page_token=next_page_token,
                delay_ms=delay_ms,
            )

        # Catch and classify HTTP errors from the YouTube API
        except HttpError as exc:

            # Check if the error indicates that comments are disabled
            if is_comments_disabled_error(exc):

                # Raise a specific error for disabled comments
                raise CommentsDisabledError(f"Comments are disabled for video {video_id}") from exc

            # Mark as partial if some comments were already collected before failure
            if comments:

                # Stop fetching but return the already collected results
                status = "partial"
                break

            # Re-raise the error if no comments were successfully fetched
            raise

        # Extract the list of comment items from the response
        items = response.get("items", [])

        # Process each item in the current page
        for item in items:

            # Build and append a new comment document to the collection
            comments.append(_build_comment_document(item, channel_id=channel_id, video_id=video_id))

            # Stop processing items if the maximum count is reached
            if len(comments) >= max_comments:
                break

        # Retrieve the token for the next page of results
        next_page_token = response.get("nextPageToken")

        # Break the loop if no further pages exist or no items were returned
        if not next_page_token or not items:
            break

    # Update status to none if the fetch succeeded but returned no comments
    if not comments and status == "ok":

        # Explicitly indicate that no comments were found
        status = "none"

    # Enrich commenter metadata and return the final results
    return _enrich_commenter_channels(client, comments, delay_ms=delay_ms), status


def _fetch_comment_page(
    client: YouTubeClient,
    *,
    video_id: str,
    max_results: int,
    page_token: str | None,
    delay_ms: int,
) -> dict[str, Any]:

    # Prepare the YouTube API request to list top-level comment threads
    request = client.service.commentThreads().list(
        part="snippet",
        videoId=video_id,
        maxResults=max_results,
        textFormat="plainText",
        pageToken=page_token,
    )

    # Execute the request and return the response dictionary
    return client.call(request, delay_ms=delay_ms)


def _build_comment_document(item: dict[str, Any], *, channel_id: str, video_id: str) -> CommentDocument:

    # Navigate the item structure to find the top-level comment snippet
    top = item.get("snippet", {}).get("topLevelComment", {})

    snippet = top.get("snippet", {})

    # Extract and normalize the author's channel ID
    author_channel_id = normalize_author_channel_id(snippet.get("authorChannelId"))

    # Return a validated CommentDocument populated with metadata
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

    # Collect unique non-null author channel IDs from the fetched comments
    channel_ids = sorted({comment.author_channel_id for comment in comments if comment.author_channel_id})

    # Return the original list if no author channels need enrichment
    if not channel_ids:

        # Nothing to enrich
        return comments

    # Initialize a map to store fetched author channel metadata
    channel_map: dict[str, dict[str, Any]] = {}

    # Fetch channel metadata in batches to minimize API requests
    for start in range(0, len(channel_ids), CHANNEL_BATCH_SIZE):

        # Prepare the current batch of channel IDs
        batch = channel_ids[start : start + CHANNEL_BATCH_SIZE]

        # Request snippet information for the batch of channels
        request = client.service.channels().list(part="snippet", id=",".join(batch))

        # Execute the hydration request
        response = client.call(request, delay_ms=delay_ms)

        # Map each returned channel snippet by its ID
        for item in response.get("items", []):

            # Extract the channel ID and its associated snippet
            author_channel_id = item.get("id")

            if author_channel_id:
                channel_map[author_channel_id] = item.get("snippet", {})

    # Create a new list for enriched comment documents
    enriched: list[CommentDocument] = []

    # Iterate through original comments and apply fetched metadata
    for comment in comments:

        # Skip enrichment if no author channel ID is present
        if not comment.author_channel_id:
            enriched.append(comment.model_copy(update={"enrichment_status": "no_channel"}))
            continue

        # Look up the author's snippet in our hydrated map
        snippet = channel_map.get(comment.author_channel_id)

        # Mark as not found if the channel metadata is missing from the API response
        if not snippet:
            enriched.append(comment.model_copy(update={"enrichment_status": "not_found"}))
            continue

        # Create an enriched copy of the comment with metadata applied
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

    # Return the collection of enriched comment documents
    return enriched
