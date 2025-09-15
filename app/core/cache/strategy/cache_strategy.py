from abc import ABC, abstractmethod
from typing import Any, Callable, Optional


class CacheStrategy(ABC):
    """
    Abstract base class for defining caching strategies.
    """

    @abstractmethod
    def get(
        self,
        key: str,
        fetch_function: Optional[Callable[[], Any]] = None,
        ttl: int = 3600,
    ) -> Any:
        """
        Retrieves data from the cache. If not found, it executes fetch_function and caches the result.

        :param key: The cache key.
        :param fetch_function: Function to fetch data if not found in cache.
        :param ttl: Time-to-live for cached data (in seconds).
        :return: The cached or fetched data.
        """
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """
        Stores data in the cache.

        :param key: The cache key.
        :param value: Data to store.
        :param ttl: Time-to-live for cached data (in seconds).
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """
        Deletes an entry from the cache.

        :param key: The cache key.
        """
        pass
