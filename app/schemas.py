from pydantic import BaseModel, Field
from typing import Any, List, Dict, Optional
from bson import ObjectId
from datetime import datetime

from app.core.helpers.embedding_helper import EmbeddingHelper
from app.domain.enums.embedding_enum import EmbeddingTypeEnum
from app.domain.enums.socialmediapost_enum import PostPlatformEnum


class InsightBase(BaseModel):
    title: str
    content: str


class InsightCreate(InsightBase):
    pass


class Insight(InsightBase):
    id: str = Field(default_factory=lambda: str(ObjectId()))
    owner_id: str

    class Config:
        from_attributes = True


class KnowledgeBase(BaseModel):
    title: str
    content: str


class KnowledgeCreate(KnowledgeBase):
    pass


class Knowledge(KnowledgeBase):
    id: str = Field(default_factory=lambda: str(ObjectId()))

    class Config:
        from_attributes = True


class GoogleData(BaseModel):
    kind: str
    items: Any


class MetaData(BaseModel):
    data: Any


class InstagramInsightsBase(BaseModel):
    user_id: str
    ig_user_id: str
    data: Any


class InstagramInsightsCreate(InstagramInsightsBase):
    pass


class InstagramInsights(InstagramInsightsBase):
    id: str


class TrackerBase(BaseModel):
    user_id: str
    name: str
    keywords: List[str]
    excluded: Optional[List[str]] = None
    tracker_type: str
    is_alert_subscribed: Optional[bool] = False
    platforms: List[str]
    locations: List[str]
    filter_duration: Optional[str] = None
    createdAt: Optional[datetime] = datetime.now()
    updatedAt: Optional[datetime] = datetime.now()


class Tracker(TrackerBase):
    tracker_id: str
    id: str = Field(default_factory=lambda: str(ObjectId()))

    class Config:
        from_attributes = True


class TrackerCreate(TrackerBase):
    pass


class TrackerUpdate(BaseModel):
    tracker_id: str
    name: str
    keywords: Optional[List[str]] = None
    excluded: Optional[List[str]] = None
    tracker_type: Optional[str] = None
    is_alert_subscribed: Optional[bool]
    platforms: Optional[List[str]] = None
    locations: Optional[List[str]] = None
    filter_duration: Optional[str] = None


class FacebookUserPagesBase(BaseModel):
    user_id: str
    data: Any


class FacebookUserPagesCreate(FacebookUserPagesBase):
    pass


class FacebookUserPages(FacebookUserPagesBase):
    page_id: Optional[str] = None
    id: str = Field(default_factory=lambda: str(ObjectId()))


class FacebookUserPagesUpdate(BaseModel):
    page_id: str
    data: Any


class HashtagBase(BaseModel):
    keyword: str  # The hashtag or keyword
    instagram_hashtag_id: str  # Hashtag ID from Instagram API
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None


class HashtagCreate(HashtagBase):
    """Schema for creating a hashtag."""

    keyword: str  # Keyword should be required
    instagram_hashtag_id: str  # Hashtag ID should be required


class HashtagUpdate(BaseModel):
    """Schema for updating a hashtag."""

    _id: str  # MongoDB internal ID
    keyword: Optional[str] = None  # Make keyword optional
    instagram_hashtag_id: Optional[str] = None  # Allow updates to Instagram ID
    updatedAt: Optional[datetime] = None


class Hashtag(HashtagBase):
    """Schema for returning a hashtag."""

    _id: str  # MongoDB internal ID
    createdAt: datetime
    updatedAt: datetime


class BaseEmbeddingModel(BaseModel):
    embedding_id: str = Field(default_factory=EmbeddingHelper.generate_db_id)
    embedding: List[float]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    embedding_type: str


class HashtagPostEmbedding(BaseEmbeddingModel):
    """Schema for a hashtag post embedding."""

    hashtag: str
    caption: Optional[str] = ""
    timestamp: Optional[str] = None
    like_count: Optional[int] = None
    comments_count: Optional[int] = None
    media_type: Optional[str] = None
    media_url: Optional[str] = None
    permalink: Optional[str] = None


class AccountPostEmbedding(BaseEmbeddingModel):
    """Schema for a account tracking post embedding."""

    _id: str
    social_user_id: str
    platform: str
    content: Optional[str] = None
    post_time: Optional[str] = None
    media_type: Optional[str] = None

    # Optional platform-specific fields
    comment_count: Optional[int] = None
    like_count: Optional[int] = None
    engagement_count: Optional[int] = None
    share_count: Optional[int] = None

    class config:
        use_enum_values = True


class PostTypeDistribution(BaseModel):
    media_type: str
    count: int


class HashtagMentionFrequency(BaseModel):
    hashtag: str
    count: int


class HashtagSummaryEmbeddingModel(BaseEmbeddingModel):
    hashtag: str
    post_count: int
    post_type_distribution: List[PostTypeDistribution]
    hashtag_mention_frequency: List[HashtagMentionFrequency]

    class config:
        use_enum_values = True
