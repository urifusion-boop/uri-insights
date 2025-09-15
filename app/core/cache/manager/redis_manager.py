import json
import asyncio
from typing import Union
import redis  # type: ignore
from app.core.config import settings
from app.domain.enums.queue_enum import QueueEnum


class RedisManager:
    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls, *args, **kwargs):
        raise RuntimeError("Use `RedisManager.get_instance()` instead")

    @classmethod
    def get_instance(cls):
        """Async Singleton instance creator"""
        if cls._instance is None:
            cls._instance = object.__new__(cls)
            cls._instance.initialize()
        return cls._instance

    def initialize(self):
        """Initialize Redis connection asynchronously"""
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            ssl=True,
        )

    def is_redis_alive(self):
        """Check Redis health status"""
        try:
            result = self.redis_client.ping()
            print(result)
        except Exception as e:
            print("Redis not working: ", e)
            return False

    def __prep_data_for_sending(self, data: Union[str, dict]):
        if isinstance(data, dict):
            return json.dumps(data)
        return data

    # Basic set and get operations
    async def set(self, key: str, value: Union[str, dict], ex=3600):
        value = self.__prep_data_for_sending(value)
        try:
            await self.redis_client.set(key, value, ex=ex)
        except Exception:
            raise

    async def get(self, key: str):
        try:
            data = await self.redis_client.get(key)
            return json.loads(data) if data else None
        except Exception:
            raise

    # Delete a key
    async def delete(self, key: str):
        await self.redis_client.delete(key)

    # Queue operations (Using Lists)
    def enqueue(self, queue_name: QueueEnum, item: Union[str, dict]):
        try:
            item = self.__prep_data_for_sending(item)
            self.redis_client.lpush(queue_name.value, item)
        except TypeError as e:
            print("TypeError occurred in JSON serialization: ", e)
        except Exception as e:
            print("Exception occurred in queueing new item: ", e)

    def dequeue(self, queue_name: str):
        data = self.redis_client.lpop(queue_name)
        return json.loads(data) if data else None

    # Redis Streams
    async def add_to_stream(self, stream_name: str, data: Union[str, dict]):
        try:
            data = self.__prep_data_for_sending(data)
            await self.redis_client.xadd(stream_name, data)
        except Exception:
            raise

    async def read_stream(self, stream_name, last_id="0", count=10, block=5000):
        try:
            return await self.redis_client.xread(
                {stream_name: last_id}, count=count, block=block
            )
        except Exception:
            raise

    # 🔹 Graceful Shutdown
    async def close_connection(self):
        """Close Redis connection"""
        try:
            await self.redis_client.close()
        except Exception:
            raise


redis_manager = RedisManager.get_instance()
