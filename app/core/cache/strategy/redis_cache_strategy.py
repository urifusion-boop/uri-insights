from typing import Any, Callable, Optional
from pymongo.collection import Collection


class RedisCacheStrategy:
    def __init__(self, db: Collection):
        # self.redis_instance = redis_manager_instance
        self.db = db

    # def get(self, key: str):
    #     return self.redis_instance.get(key)

    # def set(self, key: str, data: Any, ex=3600):
    #     self.redis_instance.set(key, data, ex)

    # def delete(self, key: str):
    #     return self.redis_instance.delete(key)
