"""Mongo upsert helper for channel_lambda."""

from __future__ import annotations

from pymongo import MongoClient, UpdateOne

from channel_job.model import ChannelDocument, Settings, dump_model


class MongoWriter:
    def __init__(self, settings: Settings) -> None:
        self._client = MongoClient(settings.mongo_uri)
        db = self._client[settings.mongo_db_name]
        self._channels = db[settings.mongo_channels_collection]

    def close(self) -> None:
        self._client.close()

    def upsert_channel(self, channel: ChannelDocument) -> int:
        doc = dump_model(channel)
        result = self._channels.bulk_write(
            [UpdateOne({"channel_id": channel.channel_id}, {"$set": doc}, upsert=True)],
            ordered=False,
        )
        return result.upserted_count + result.modified_count
