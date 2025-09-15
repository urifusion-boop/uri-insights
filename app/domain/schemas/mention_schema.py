from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from bson import ObjectId

from app.domain.enums.mention_enum import SentimentEnum, SentimentPriorityEnum


class MentionBase(BaseModel):
    mention_id: str = Field(default_factory=lambda: str(ObjectId()))  # Unique ID
    user_id: str  # ID of the user tracking the mention
    keyword: str  # The keyword associated with the mention
    title: Optional[str] = None  # Title of the mention
    comment: Optional[str] = None  # Comment or snippet of the mention
    author: Optional[str] = None  # Author of the mention
    image: Optional[str] = None  # Image associated with the mention
    timestamp: Optional[datetime] | str = None  # Time when the mention occurred
    website: Optional[str] = None  # Website or source of the mention
    platform: Optional[str] = None  # Platform of the mention
    sentiment: Optional[SentimentEnum] = None
    sentiment_score: Optional[float] = None
    sentiment_priority: Optional[SentimentPriorityEnum] = None
    is_read: bool = False
    deleted: bool = False  # Whether the mention has been marked as deleted
    starred: bool = False  # Whether the mention has been marked as starred
    processed: bool = False  # Whether the mention has been processed for leads tracking
    created_at: datetime = Field(default_factory=datetime.utcnow)  # Creation timestamp
    updated_at: datetime = Field(default_factory=datetime.utcnow)  # Update timestamp

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
        use_enum_values = True


class MentionCreate(MentionBase):
    """
    Inherits from MentionBase but excludes fields managed by the system.
    """

    pass


class MentionUpdate(BaseModel):
    """
    Fields allowed when updating a mention.
    Excludes system-managed fields like mention_id, user_id, and created_at.
    """

    title: Optional[str] = None
    comment: Optional[str] = None
    author: Optional[str] = None
    image: Optional[str] = None
    timestamp: Optional[datetime] | str = None
    website: Optional[str] = None
    is_read: Optional[bool] = None
    deleted: Optional[bool] = None
    starred: Optional[bool] = None
    processed: Optional[bool] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class Mention(MentionBase):
    """
    Complete schema for a mention, including system fields like ObjectId.
    """

    id: str = Field(default_factory=lambda: str(ObjectId()))  # MongoDB ObjectId

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
