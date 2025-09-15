from enum import Enum


class EmbeddingModelEnum(Enum):
    ADA = "text-embedding-ada-002"


class EmbeddingTypeEnum(Enum):
    HASHTAG_TRACKING_EMBEDDING = "HASHTAG_TRACKING_EMBEDDING"
    ACCOUNT_TRACKING_EMBEDDING = "ACCOUNT_TRACKING_EMBEDDING"
