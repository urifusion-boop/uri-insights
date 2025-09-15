from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import os
import threading
from typing import Optional, Union
import psutil
import gc


class BasePoolManager:
    """
    A manager for a process pool.
    """

    executor_classes = {
        "process": ProcessPoolExecutor,
        "thread": ThreadPoolExecutor,
    }

    _lock = threading.Lock()
    _instance = None
    _executor = None
    num_workers = 0

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls, *args, **kwargs)
                    cls.num_workers = cls.__calculate_optimal_num_workers()
                    cls._executor = None
        return cls._instance

    @classmethod
    def __calculate_optimal_num_workers(cls):
        cpu_count = os.cpu_count() or 4
        load_percentage = psutil.cpu_percent(interval=1)

        # Scale worker count dynamically based on CPU load
        if load_percentage < 50:
            return cpu_count
        elif load_percentage < 75:
            return max(2, cpu_count // 2)
        else:
            return max(1, cpu_count // 4)

    @classmethod
    def get_num_workers(cls):
        return cls.num_workers

    @classmethod
    def get_executor(
        cls, executor_type: str = "process"
    ) -> Union[ProcessPoolExecutor, ThreadPoolExecutor]:
        if not cls._instance:
            cls._instance = cls()
        if cls._executor is None:
            with cls._lock:
                if cls._executor is None:  # Double-check locking
                    cls._executor = cls.executor_classes[executor_type](
                        max_workers=cls.num_workers
                    )
        return cls._executor

    @classmethod
    def shutdown(cls):
        with cls._lock:
            if cls._executor:
                cls._executor.shutdown(wait=True)
                cls._executor = None
                cls.num_workers = 0

                # Explicitly trigger garbage collection to clean up processes
                gc.collect()

                # Reset instance after cleanup is fully completed
                cls._instance = None
