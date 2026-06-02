"""Mongo upsert helper for comment_lambda."""

from __future__ import annotations

from pymongo import MongoClient, UpdateOne

from comment_job.model import CommentDocument, Settings, dump_model


class MongoWriter:
    def __init__(self, settings: Settings) -> None:
        self._client = MongoClient(settings.mongo_uri)
        db = self._client[settings.mongo_db_name]
        self._videos = db[settings.mongo_videos_collection]
        self._comments = db[settings.mongo_comments_collection]

    def close(self) -> None:
        self._client.close()

    def upsert_comments(self, comments: list[CommentDocument]) -> int:
        operations: list[UpdateOne] = []
        for comment in comments:
            operations.append(UpdateOne({"comment_id": comment.comment_id}, {"$set": dump_model(comment)}, upsert=True))

        if not operations:
            return 0
        result = self._comments.bulk_write(operations, ordered=False)
        return result.upserted_count + result.modified_count

    def update_video_comment_status(self, video_id: str, *, comments_status: str, comments_fetched: int, error: str | None) -> int:
        update = {
            "comments_status": comments_status,
            "comments_fetched": comments_fetched,
            "comments_error": error,
        }
        result = self._videos.update_one({"video_id": video_id}, {"$set": update}, upsert=True)
        return int(result.upserted_id is not None or result.modified_count > 0)
