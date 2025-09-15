from app.core.cache.strategy.cache_strategy import CacheStrategy
from typing import Any, Callable, Optional


class CacheService:
    """
    Handles cache operations using a given cache strategy.
    """

    def __init__(self, strategy: CacheStrategy):
        """
        Initializes CacheService with a specified caching strategy.

        :param strategy: The caching strategy to use.
        """
        self.strategy = strategy

    def get(
        self,
        key: str,
        fetch_function: Optional[Callable[[], Any]] = None,
        ttl: int = 3600,
    ) -> Any:
        """
        Retrieves data from cache. If not found, fetches data and stores it.

        :param key: The cache key.
        :param fetch_function: Function to fetch data if not found.
        :param ttl: Time-to-live for cached data (in seconds).
        :return: Cached or fetched data.
        """
        return self.strategy.get(key, fetch_function, ttl)

    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """
        Stores data in cache.

        :param key: The cache key.
        :param value: The value to store.
        :param ttl: Time-to-live for cached data (in seconds).
        """
        self.strategy.set(key, value, ttl)

    def delete(self, key: str) -> None:
        """
        Deletes a cache entry.

        :param key: The cache key.
        """
        self.strategy.delete(key)
