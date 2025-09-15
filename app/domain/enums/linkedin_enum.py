from enum import Enum


class LinkedInMediaShareTypeEnum(Enum):
    IMAGE = "image"
    VIDEO = "video"


class LinkedInVisibilityEnum(Enum):
    PUBLIC = "PUBLIC"
    CONNECTIONS = "CONNECTIONS"


class LinkedinUrnNamespaceEnum(Enum):
    PERSON = "PERSON"
    SHARE = "SHARE"
    ORIGINALARTICLE = "ORIGINALARTICLE"
    UGCPOST = "UGCPOST"
    COMMENT = "COMMENT"
    LIKE = "LIKE"
    ORGANIZATION = "ORGANIZATION"


class LinkedInTokenScopeEnum(Enum):
    CONTENT_MANAGEMENT = "CONTENT_MANAGEMENT"
    ACCOUNT_TRACKING = "ACCOUNT_TRACKING"


class LinkedInPostRetrievalOrderEnum(Enum):
    LAST_MODIFIED = "LAST_MODIFIED"
    CREATED = "CREATED"


class LinkedInTimeGranularityEnum(Enum):
    DAY = "DAY"
    WEEK = "WEEK"
    MONTH = "MONTH"


class LinkedInReactionTypeEnum(Enum):
    CHRONOLOGICAL = "CHRONOLOGICAL"
    REVERSE_CHRONOLOGICAL = "REVERSE_CHRONOLOGICAL"
    RELEVANCE = "RELEVANCE"
