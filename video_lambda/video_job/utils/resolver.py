"""Video fetching and hydration for video_lambda."""

from __future__ import annotations

from video_job.client.youtube import YouTubeClient
from video_job.model import VideoDocument
from video_job.utils.batching import VIDEO_BATCH_SIZE, iter_batches
from video_job.utils.youtube_items import extract_video_id


def fetch_latest_video_documents(
    client: YouTubeClient,
    channel_id: str,
    *,
    max_videos: int,
    delay_ms: int,
) -> list[VideoDocument]:
    uploads_playlist_id = _get_uploads_playlist_id(client, channel_id, delay_ms=delay_ms)
    if not uploads_playlist_id:
        return []

    video_ids = _collect_upload_video_ids(
        client,
        uploads_playlist_id,
        max_videos=max_videos,
        delay_ms=delay_ms,
    )
    return _hydrate_video_documents(client, channel_id, video_ids, delay_ms=delay_ms)


def _get_uploads_playlist_id(client: YouTubeClient, channel_id: str, *, delay_ms: int) -> str | None:
    request = client.service.channels().list(part="contentDetails", id=channel_id)
    response = client.call(request, delay_ms=delay_ms)
    items = response.get("items", [])
    if not items:
        return None

    uploads_playlist_id = items[0].get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
    return uploads_playlist_id if isinstance(uploads_playlist_id, str) and uploads_playlist_id else None


def _collect_upload_video_ids(
    client: YouTubeClient,
    uploads_playlist_id: str,
    *,
    max_videos: int,
    delay_ms: int,
) -> list[str]:
    video_ids: list[str] = []
    next_page_token: str | None = None
    while len(video_ids) < max_videos:
        request = client.service.playlistItems().list(
            part="contentDetails",
            playlistId=uploads_playlist_id,
            maxResults=min(50, max_videos - len(video_ids)),
            pageToken=next_page_token,
        )
        response = client.call(request, delay_ms=delay_ms)
        for item in response.get("items", []):
            video_id = extract_video_id(item)
            if video_id:
                video_ids.append(video_id)
                if len(video_ids) >= max_videos:
                    break
        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return video_ids


def _hydrate_video_documents(
    client: YouTubeClient,
    channel_id: str,
    video_ids: list[str],
    *,
    delay_ms: int,
) -> list[VideoDocument]:
    videos: list[VideoDocument] = []
    for batch_ids in iter_batches(video_ids, VIDEO_BATCH_SIZE):
        request = client.service.videos().list(part="snippet", id=",".join(batch_ids))
        response = client.call(request, delay_ms=delay_ms)
        snippet_map = {item["id"]: item.get("snippet", {}) for item in response.get("items", []) if item.get("id")}
        for video_id in batch_ids:
            snippet = snippet_map.get(video_id, {})
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
    return videos
