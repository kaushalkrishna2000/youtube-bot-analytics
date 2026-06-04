"""Video fetching and hydration for video_lambda."""

from __future__ import annotations

from video_job.client.youtube import YouTubeClient
from video_job.model import VideoDocument
from video_job.utils.batching import VIDEO_BATCH_SIZE, iter_batches
from video_job.utils.youtube_items import extract_video_id


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------


def fetch_latest_video_documents(
    client: YouTubeClient,
    channel_id: str,
    *,
    max_videos: int,
    delay_ms: int,
) -> list[VideoDocument]:

    # Resolve the uploads playlist ID for the specified channel
    uploads_playlist_id = _get_uploads_playlist_id(client, channel_id, delay_ms=delay_ms)

    # Return an empty list if no uploads playlist was found
    if not uploads_playlist_id:

        # No content available for this channel
        return []

    # Collect the set of individual video IDs from the uploads playlist
    video_ids = _collect_upload_video_ids(
        client,
        uploads_playlist_id,
        max_videos=max_videos,
        delay_ms=delay_ms,
    )

    # Hydrate and return full video documents for the collected IDs
    return _hydrate_video_documents(client, channel_id, video_ids, delay_ms=delay_ms)


# -----------------------------------------------------------------------------
# Private Helpers
# -----------------------------------------------------------------------------


def _get_uploads_playlist_id(client: YouTubeClient, channel_id: str, *, delay_ms: int) -> str | None:

    # Prepare a request to list content details for the channel
    request = client.service.channels().list(part="contentDetails", id=channel_id)

    # Execute the API call with optional throttling
    response = client.call(request, delay_ms=delay_ms)

    # Extract the list of channel items from the response
    items = response.get("items", [])

    # Return None if the channel does not exist
    if not items:

        # No channel metadata available
        return None

    # Retrieve the uploads playlist identifier from related playlists
    uploads_playlist_id = items[0].get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")

    # Return the validated playlist ID or None if missing
    return uploads_playlist_id if isinstance(uploads_playlist_id, str) and uploads_playlist_id else None


def _collect_upload_video_ids(
    client: YouTubeClient,
    uploads_playlist_id: str,
    *,
    max_videos: int,
    delay_ms: int,
) -> list[str]:

    # Initialize a list to store collected video identifiers
    video_ids: list[str] = []

    # Track the token for the next page of results
    next_page_token: str | None = None

    # Continue fetching pages until the limit is reached or no more pages exist
    while len(video_ids) < max_videos:

        # Prepare a request to list items in the uploads playlist
        request = client.service.playlistItems().list(
            part="contentDetails",
            playlistId=uploads_playlist_id,
            maxResults=min(50, max_videos - len(video_ids)),
            pageToken=next_page_token,
        )

        # Execute the playlist items lookup
        response = client.call(request, delay_ms=delay_ms)

        # Extract video IDs from each item in the current page
        for item in response.get("items", []):

            # Parse the video ID from the playlist item structure
            video_id = extract_video_id(item)

            # Append the ID if it was successfully extracted
            if video_id:

                # Add to the running collection
                video_ids.append(video_id)

                # Stop if we have reached the requested maximum
                if len(video_ids) >= max_videos:
                    break

        # Retrieve the token for the next page of playlist items
        next_page_token = response.get("nextPageToken")

        # Break the loop if no further pages are available
        if not next_page_token:
            break

    # Return the final list of collected video IDs
    return video_ids


def _hydrate_video_documents(
    client: YouTubeClient,
    channel_id: str,
    video_ids: list[str],
    *,
    delay_ms: int,
) -> list[VideoDocument]:

    # Initialize a list to hold the fully hydrated video documents
    videos: list[VideoDocument] = []

    # Process video IDs in batches to optimize API usage
    for batch_ids in iter_batches(video_ids, VIDEO_BATCH_SIZE):

        # Request snippet metadata for all video IDs in the current batch
        request = client.service.videos().list(part="snippet", id=",".join(batch_ids))

        # Execute the batch hydration request
        response = client.call(request, delay_ms=delay_ms)

        # Create a mapping from video ID to snippet data for alignment
        snippet_map = {item["id"]: item.get("snippet", {}) for item in response.get("items", []) if item.get("id")}

        # Create a document for each ID to preserve the original playlist order
        for video_id in batch_ids:

            # Retrieve the snippet from the map or use an empty default
            snippet = snippet_map.get(video_id, {})

            # Append a new VideoDocument to the final collection
            videos.append(
                VideoDocument(
                    video_id=video_id,
                    channel_id=channel_id,
                    title=snippet.get("title", ""),
                    published_at=snippet.get("publishedAt", ""),
                    comments_status="pending",
                    comments_fetched=0,
                )
            )

    # Return the ordered list of fully populated video documents
    return videos
