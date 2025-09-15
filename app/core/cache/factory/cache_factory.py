from pymongo.collection import Collection
from app.services.CacheService import CacheService
from app.core.cache.strategy.mongo_cache_strategy import MongoCacheStrategy
from app.domain.enums.cache_enum import CachePolicyEnum


class CacheFactory:
    """
    Factory for creating and managing cache instances based on policies.
    """

    _instances: dict = {}

    @staticmethod
    def get_cache_instance(policy: CachePolicyEnum, db: Collection) -> CacheService:
        """
        Retrieves a cache instance based on the specified policy.

        :param policy: The caching policy to apply.
        :param db: The MongoDB collection to use for caching.
        :return: CacheService instance.
        """
        if policy not in CacheFactory._instances:
            if policy == CachePolicyEnum.READ_THROUGH:
                CacheFactory._instances[policy] = CacheService(MongoCacheStrategy(db))
            else:
                raise ValueError(f"Unsupported cache policy: {policy}")

        return CacheFactory._instances[policy]
