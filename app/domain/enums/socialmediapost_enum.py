from enum import Enum


class MediaTypeEnum(str, Enum):
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    GIF = "GIF"
    TEXT = "TEXT"


class PostStatusEnum(str, Enum):
    QUEUED = "QUEUED"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"
    SCHEDULED = "SCHEDULED"
    DRAFT = "DRAFT"


class PostPlatformEnum(str, Enum):
    LINKEDIN = "LINKEDIN"
    TWITTER = "TWITTER"
    TIKTOK = "TIKTOK"
    INSTAGRAM = "INSTAGRAM"
    FACEBOOK = "FACEBOOK"


class PostTypeEnum(str, Enum):
    # Instagram and facebook specific types
    REEL = "REEL"
    STORY = "STORY"
    POST = "POST"
    # LinkedIn-specific types
    TEXT_SHARE = "TEXT_SHARE"
    ARTICLE_SHARE = "ARTICLE_SHARE"
    MEDIA_SHARE = "MEDIA_SHARE"
    # Twitter/X-specific types
    TWEET = "TWEET"
    THREAD = "THREAD"

    # TikTok-specific types
    TIKTOK_VIDEO = "TIKTOK_VIDEO"
    TIKTOK_IMAGE = "TIKTOK_IMAGE"
