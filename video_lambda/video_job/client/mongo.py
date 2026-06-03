"""Mongo upsert helper for video_lambda."""

from __future__ import annotations

from pymongo import MongoClient, UpdateOne

from video_job.model import Settings, VideoDocument, dump_model


class MongoWriter:
    """Writes video-stage documents to MongoDB."""

    def __init__(self, settings: Settings) -> None:

        # Connect to the MongoDB server using the provided URI
        self._client = MongoClient(settings.mongo_uri)

        # Select the target database from the client
        db = self._client[settings.mongo_db_name]

        # Initialize the videos collection reference
        self._videos = db[settings.mongo_videos_collection]

    def close(self) -> None:

        # Close the underlying MongoDB client connection
        self._client.close()

    def upsert_videos(self, videos: list[VideoDocument]) -> int:

        # Initialize a list to hold bulk update operations
        operations: list[UpdateOne] = []

        # Iterate through the provided video documents
        for video in videos:

            # Create an upsert operation matching by video ID
            operations.append(UpdateOne({"video_id": video.video_id}, {"$set": dump_model(video)}, upsert=True))

        # Return zero if no operations were created
        if not operations:

            # No videos to update
            return 0

        # Execute the bulk write operation in an unordered fashion
        result = self._videos.bulk_write(operations, ordered=False)

        # Return the sum of inserted and modified document counts
        return result.upserted_count + result.modified_count
