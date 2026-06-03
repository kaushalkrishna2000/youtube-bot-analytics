"""Mongo upsert helper for channel_lambda."""

from __future__ import annotations

from pymongo import MongoClient, UpdateOne

from channel_job.model import ChannelDocument, Settings, dump_model


class MongoWriter:
    """Writes channel-stage documents to MongoDB."""

    def __init__(self, settings: Settings) -> None:

        # Connect to the MongoDB server using the provided URI
        self._client = MongoClient(settings.mongo_uri)

        # Select the target database from the client
        db = self._client[settings.mongo_db_name]

        # Initialize the channels collection reference
        self._channels = db[settings.mongo_channels_collection]

    def close(self) -> None:

        # Close the underlying MongoDB client connection
        self._client.close()

    def upsert_channel(self, channel: ChannelDocument) -> int:

        # Convert the channel model into a dictionary for storage
        doc = dump_model(channel)

        # Perform a bulk upsert operation matching by channel ID
        result = self._channels.bulk_write(
            [UpdateOne({"channel_id": channel.channel_id}, {"$set": doc}, upsert=True)],
            ordered=False,
        )

        # Return the sum of inserted and modified document counts
        return result.upserted_count + result.modified_count
