from enum import Enum


class SourceTypeEnum(str, Enum):
    FILE_UPLOAD = "FILE_UPLOAD"
    PULL_FROM_URL = "PULL_FROM_URL"


class PrivacyLevelEnum(str, Enum):
    PUBLIC_TO_EVERYONE = "PUBLIC_TO_EVERYONE"
    MUTUAL_FOLLOW_FRIENDS = "MUTUAL_FOLLOW_FRIENDS"
    SELF_ONLY = "SELF_ONLY"


class TiktokMediaTypeEnum(str, Enum):
    VIDEO = "VIDEO"
    PHOTO = "PHOTO"
