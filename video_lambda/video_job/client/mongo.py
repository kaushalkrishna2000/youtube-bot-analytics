"""Mongo upsert helper for video_lambda."""

from __future__ import annotations

from pymongo import MongoClient, UpdateOne

from video_job.model import Settings, VideoDocument, dump_model


class MongoWriter:
    def __init__(self, settings: Settings) -> None:
        self._client = MongoClient(settings.mongo_uri)
        db = self._client[settings.mongo_db_name]
        self._videos = db[settings.mongo_videos_collection]

    def close(self) -> None:
        self._client.close()

    def upsert_videos(self, videos: list[VideoDocument]) -> int:
        operations: list[UpdateOne] = []
        for video in videos:
            operations.append(UpdateOne({"video_id": video.video_id}, {"$set": dump_model(video)}, upsert=True))

        if not operations:
            return 0
        result = self._videos.bulk_write(operations, ordered=False)
        return result.upserted_count + result.modified_count
