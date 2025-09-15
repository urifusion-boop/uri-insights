from enum import Enum
from typing import Dict
from ..config import settings


class QueueEnumTypeHelper:
    @staticmethod
    def create_queue_type_enums(cls, enum_names: Dict[str, str]) -> None:
        """Dynamically creates an Enum with environment-specific suffix."""
        suffix = "_live" if settings.DEV_ENV == "Production" else "_test"

        # Modify the dictionary values based on the environment
        for key, value in enum_names.items():
            setattr(cls, key, f"{value}{suffix}")
