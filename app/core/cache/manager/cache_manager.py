from typing import Optional
from app.database import get_db
from app.core.cache.factory.cache_factory import CacheFactory
from app.services.CacheService import CacheService
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.enums.cache_enum import CachePolicyEnum


class CacheManager:
    """
    Singleton manager for caching service.
    Ensures a globally shared instance of CacheService.
    """

    _cache_service: Optional[CacheService] = None

    @staticmethod
    def initialize() -> None:
        """
        Initializes the cache service using the existing MongoDB connection.
        """
        if CacheManager._cache_service is None:
            db: AsyncIOMotorDatabase = get_db()
            CacheManager._cache_service = CacheFactory.get_cache_instance(
                CachePolicyEnum.READ_THROUGH, db
            )

    @staticmethod
    def get_cache_service() -> CacheService:
        """
        Retrieves the shared cache service instance.

        :return: CacheService instance.
        :raises ValueError: If CacheManager is not initialized.
        """
        if CacheManager._cache_service is None:
            raise ValueError(
                "CacheManager is not initialized. Call CacheManager.initialize() first."
            )
        return CacheManager._cache_service
