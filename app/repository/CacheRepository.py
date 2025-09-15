from datetime import datetime, timedelta
from typing import Any, Optional, Dict
from motor.motor_asyncio import AsyncIOMotorDatabase


class CacheRepository:
    DEFAULT_CACHE_TTL = timedelta(hours=1)  # Default TTL for cache entries

    @staticmethod
    async def get_cache(db: AsyncIOMotorDatabase, cache_key: str) -> Optional[Any]:
        """Retrieve a cached entry by its key if it hasn't expired. Delete if expired."""
        cached_data = await db["cache"].find_one({"cache_key": cache_key})
        if cached_data:
            expiry_date = cached_data.get("expires_at")
            if not expiry_date or expiry_date > datetime.utcnow():
                return cached_data["data"]
            else:
                await db["cache"].delete_one({"cache_key": cache_key})
        return None

    @staticmethod
    async def set_cache(
        db: AsyncIOMotorDatabase,
        cache_key: str,
        data: Any,
        ttl: timedelta = DEFAULT_CACHE_TTL,
    ) -> None:
        """Set a cache entry with a custom expiration time."""
        now = datetime.utcnow()
        cache_entry = {
            "cache_key": cache_key,
            "data": data,
            "created_at": now,
        }
        if ttl:
            cache_entry["expires_at"] = now + ttl
        await db["cache"].replace_one(
            {"cache_key": cache_key}, cache_entry, upsert=True
        )

    @staticmethod
    async def clear_cache(db: AsyncIOMotorDatabase, cache_key: str) -> bool:
        """Clear a specific cache entry by its key."""
        result = await db["cache"].delete_one({"cache_key": cache_key})
        await CacheRepository.clear_expired_cache(db)
        return result.deleted_count > 0

    @staticmethod
    async def clear_expired_cache(db: AsyncIOMotorDatabase) -> int:
        """Clear all expired cache entries."""
        result = await db["cache"].delete_many(
            {"expires_at": {"$lt": datetime.utcnow()}}
        )
        return result.deleted_count

    @staticmethod
    async def clear_all_cache(db: AsyncIOMotorDatabase) -> int:
        """Clear all cache entries."""
        result = await db["cache"].delete_many({})
        return result.deleted_count

    @staticmethod
    async def clear_cache_by_contains(db: AsyncIOMotorDatabase, substring: str) -> int:
        """
        Clear all cache entries where the `cache_key` contains the specified substring.
        """
        query = {"cache_key": {"$regex": f".*{substring}.*"}}
        result = await db["cache"].delete_many(query)
        return result.deleted_count
