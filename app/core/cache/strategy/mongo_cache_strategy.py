from typing import Any, Callable, Optional
from pymongo.collection import Collection
from datetime import datetime, timedelta
from app.core.cache.strategy.cache_strategy import CacheStrategy


class MongoCacheStrategy(CacheStrategy):
    """
    Implementation of the CacheStrategy interface using MongoDB as the caching backend.
    """

    def __init__(self, db: Collection):
        """
        Initializes MongoCacheStrategy with a MongoDB collection.

        :param db: MongoDB collection to store cache entries.
        """
        self.db = db

    def get(
        self,
        key: str,
        fetch_function: Optional[Callable[[], Any]] = None,
        ttl: int = 3600,
    ) -> Any:
        """
        Retrieves data from MongoDB cache. If not found, executes fetch_function and caches the result.

        :param key: The cache key.
        :param fetch_function: Function to fetch data if not found.
        :param ttl: Time-to-live for cached data (in seconds).
        :return: Cached or fetched data.
        """
        cache_entry = self.db.find_one({"cache_key": key})
        if cache_entry and cache_entry["expires_at"] > datetime.utcnow():
            return cache_entry["data"]

        if fetch_function:
            data = fetch_function()
            self.set(key, data, ttl)
            return data

        return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """
        Stores data in MongoDB cache with an expiration time.

        :param key: The cache key.
        :param value: The data to store.
        :param ttl: Time-to-live for cached data (in seconds).
        """
        self.db.replace_one(
            {"cache_key": key},
            {
                "cache_key": key,
                "data": value,
                "expires_at": datetime.utcnow() + timedelta(seconds=ttl),
            },
            upsert=True,
        )

    def delete(self, key: str) -> None:
        """
        Deletes a specific cache entry.

        :param key: The cache key to delete.
        """
        self.db.delete_one({"cache_key": key})
