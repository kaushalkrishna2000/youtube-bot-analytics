"""Mongo upsert helper for comment_lambda."""

from __future__ import annotations

from pymongo import MongoClient, UpdateOne

from comment_job.model import CommentDocument, Settings, dump_model


class MongoWriter:
    """Writes comment-stage documents and video comment status to MongoDB."""

    def __init__(self, settings: Settings) -> None:
        """Open MongoDB collections using Lambda settings.

        Args:
            settings: Loaded comment Lambda settings with Mongo connection
                details.
        """
        self._client = MongoClient(settings.mongo_uri)
        db = self._client[settings.mongo_db_name]
        self._videos = db[settings.mongo_videos_collection]
        self._comments = db[settings.mongo_comments_collection]

    def close(self) -> None:
        """Close the underlying MongoDB client."""
        self._client.close()

    def upsert_comments(self, comments: list[CommentDocument]) -> int:
        """Upsert comment documents by ``comment_id``.

        Args:
            comments: Comment documents to write.

        Returns:
            Number of inserted or modified MongoDB documents.
        """
        operations: list[UpdateOne] = []
        for comment in comments:
            operations.append(UpdateOne({"comment_id": comment.comment_id}, {"$set": dump_model(comment)}, upsert=True))

        if not operations:
            return 0
        # Unordered bulk writes keep independent comment updates moving even if
        # MongoDB has to handle one operation differently.
        result = self._comments.bulk_write(operations, ordered=False)
        return result.upserted_count + result.modified_count

    def update_video_comment_status(self, video_id: str, *, comments_status: str, comments_fetched: int, error: str | None) -> int:
        """Persist the comment-fetch outcome on the parent video document.

        Args:
            video_id: YouTube video ID to update.
            comments_status: Fetch status recorded by the comment resolver.
            comments_fetched: Number of comments fetched for the video.
            error: Optional error message for disabled or failed comments.

        Returns:
            ``1`` when MongoDB inserted or modified the video status, otherwise
            ``0``.
        """
        update = {
            "comments_status": comments_status,
            "comments_fetched": comments_fetched,
            "comments_error": error,
        }
        result = self._videos.update_one({"video_id": video_id}, {"$set": update}, upsert=True)
        return int(result.upserted_id is not None or result.modified_count > 0)
