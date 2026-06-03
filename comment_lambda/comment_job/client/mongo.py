"""Mongo upsert helper for comment_lambda."""

from __future__ import annotations

from pymongo import MongoClient, UpdateOne

from comment_job.model import CommentDocument, Settings, dump_model


class MongoWriter:
    """Writes comment-stage documents and video comment status to MongoDB."""

    def __init__(self, settings: Settings) -> None:

        # Connect to the MongoDB server using the provided URI
        self._client = MongoClient(settings.mongo_uri)

        # Select the target database from the client
        db = self._client[settings.mongo_db_name]

        # Initialize the videos collection reference
        self._videos = db[settings.mongo_videos_collection]

        # Initialize the comments collection reference
        self._comments = db[settings.mongo_comments_collection]

    def close(self) -> None:

        # Close the underlying MongoDB client connection
        self._client.close()

    def upsert_comments(self, comments: list[CommentDocument]) -> int:

        # Initialize a list to hold bulk update operations
        operations: list[UpdateOne] = []

        # Iterate through the provided comment documents
        for comment in comments:

            # Create an upsert operation matching by comment ID
            operations.append(UpdateOne({"comment_id": comment.comment_id}, {"$set": dump_model(comment)}, upsert=True))

        # Return zero if no operations were created
        if not operations:

            # No comments to update
            return 0

        # Execute the bulk write operation in an unordered fashion
        result = self._comments.bulk_write(operations, ordered=False)

        # Return the sum of inserted and modified document counts
        return result.upserted_count + result.modified_count

    def update_video_comment_status(self, video_id: str, *, comments_status: str, comments_fetched: int, error: str | None) -> int:

        # Prepare the status update payload for the video
        update = {
            "comments_status": comments_status,
            "comments_fetched": comments_fetched,
            "comments_error": error,
        }

        # Perform the update on the video document matching by ID
        result = self._videos.update_one({"video_id": video_id}, {"$set": update}, upsert=True)

        # Return 1 if a document was affected, otherwise 0
        return int(result.upserted_id is not None or result.modified_count > 0)
