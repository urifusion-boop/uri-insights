# Enums
from enum import Enum


class CachePolicyEnum(Enum):
    READ_THROUGH = ("READ_THROUGH",)
    WRITE_THROUGH = ("WRITE_THROUGH",)
    WRITE_BEHIND = ("WRITE_BEHIND",)
