from .BasePoolManager import BasePoolManager


class ThreadPoolManager(BasePoolManager):
    @classmethod
    def get_executor(cls, executor_type: str = "thread"):
        return super().get_executor(executor_type=executor_type)


thread_pool_manager = ThreadPoolManager()
