from enum import Enum


class SentimentPriorityEnum(Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class SentimentEnum(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
