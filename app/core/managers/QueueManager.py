import asyncio
from typing import Dict, Optional


class QueueManager:
    _instance: Optional["QueueManager"] = None

    def __init__(self, max_queues: int = 10, queue_size: int = 10):
        if QueueManager._instance is not None:
            raise RuntimeError("This class is a singleton!")
        self.max_queues = max_queues
        self.queue_size = queue_size
        self.queues: Dict[tuple, asyncio.Queue] = (
            {}
        )  # Stores producer-consumer queue mappings
        self.lock = asyncio.Lock()  # Ensures safe modification of queues

    @classmethod
    def get_instance(cls) -> "QueueManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def get_queue(self, producer_id: str, consumer_id: str) -> asyncio.Queue:
        key = (producer_id, consumer_id)
        async with self.lock:
            if key not in self.queues.keys():
                if len(self.queues) >= self.max_queues:
                    raise RuntimeError("Maximum number of queues reached")
                self.queues[key] = asyncio.Queue(self.queue_size)
            return self.queues[key]

    async def remove_queue(self, producer_id: str, consumer_id: str):
        key = (producer_id, consumer_id)
        async with self.lock:
            if key in self.queues:
                del self.queues[key]


queue_manager = QueueManager()
