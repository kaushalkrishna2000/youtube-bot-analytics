"""Mongo upsert helper for video_lambda."""

from __future__ import annotations

from pymongo import MongoClient, UpdateOne

from video_job.model import Settings, VideoDocument, dump_model


class MongoWriter:
    """Writes video-stage documents to MongoDB."""

    def __init__(self, settings: Settings) -> None:
        """Open MongoDB collections using Lambda settings.

        Args:
            settings: Loaded video Lambda settings with Mongo connection
                details.
        """
        self._client = MongoClient(settings.mongo_uri)
        db = self._client[settings.mongo_db_name]
        self._videos = db[settings.mongo_videos_collection]

    def close(self) -> None:
        """Close the underlying MongoDB client."""
        self._client.close()

    def upsert_videos(self, videos: list[VideoDocument]) -> int:
        """Upsert video documents by ``video_id``.

        Args:
            videos: Video documents to write.

        Returns:
            Number of inserted or modified MongoDB documents.
        """
        operations: list[UpdateOne] = []
        for video in videos:
            operations.append(UpdateOne({"video_id": video.video_id}, {"$set": dump_model(video)}, upsert=True))

        if not operations:
            return 0
        # Unordered bulk writes keep independent video updates moving even if
        # MongoDB has to handle one operation differently.
        result = self._videos.bulk_write(operations, ordered=False)
        return result.upserted_count + result.modified_count
