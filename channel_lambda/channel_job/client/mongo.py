"""Mongo upsert helper for channel_lambda."""

from __future__ import annotations

from pymongo import MongoClient, UpdateOne

from channel_job.model import ChannelDocument, Settings, dump_model


class MongoWriter:
    """Writes channel-stage documents to MongoDB."""

    def __init__(self, settings: Settings) -> None:
        """Open MongoDB collections using Lambda settings.

        Args:
            settings: Loaded channel Lambda settings with Mongo connection
                details.
        """
        self._client = MongoClient(settings.mongo_uri)
        db = self._client[settings.mongo_db_name]
        self._channels = db[settings.mongo_channels_collection]

    def close(self) -> None:
        """Close the underlying MongoDB client."""
        self._client.close()

    def upsert_channel(self, channel: ChannelDocument) -> int:
        """Upsert one channel document by ``channel_id``.

        Args:
            channel: Channel document to write.

        Returns:
            Number of inserted or modified MongoDB documents.
        """
        doc = dump_model(channel)
        result = self._channels.bulk_write(
            [UpdateOne({"channel_id": channel.channel_id}, {"$set": doc}, upsert=True)],
            ordered=False,
        )
        return result.upserted_count + result.modified_count
