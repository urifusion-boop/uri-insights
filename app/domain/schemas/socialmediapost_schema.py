from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Union
from datetime import datetime, date, time
from app.domain.enums.socialmediapost_enum import (
    PostStatusEnum,
    PostTypeEnum,
    MediaTypeEnum,
)
from bson import ObjectId

from app.domain.requests.facebook_requests import FacebookSocialMediaPostSettings
from app.domain.requests.linkedin_requests import LinkedinSocialMediaPostSettings
from app.domain.requests.tiktok_requests import TiktokSocialMediaPostSettings


# MediaItem Model
class MediaItem(BaseModel):
    url: str  # URL of the media item
    media_type: MediaTypeEnum  # Enum for media types
    caption: Optional[str] = None  # Optional caption for media
    alt_text: Optional[str] = None  # Accessibility description


# Base Model
class SocialMediaPostBase(BaseModel):
    post_id: str = Field(
        default_factory=lambda: str(ObjectId()),
        description="Unique identifier for the post",
    )
    user_id: str = Field(
        ..., description="Unique identifier for the user owning this post"
    )
    influencer_id: str = Field(
        ..., description="Unique identifier for the influencer owning this post"
    )
    social_user_id: str = Field(
        ..., description="Unique social media account identifier for the influencer"
    )
    platform: str = Field(
        ..., description="The platform for this post, e.g., 'instagram', 'linkedin'"
    )
    post_type: PostTypeEnum = Field(
        ..., description="The specific type of post for the given platform"
    )
    content: Optional[str] = Field(
        None, max_length=5000, description="Main post content"
    )  # Optional for media-only posts
    media: Optional[List[MediaItem]] = None  # List of media items
    hashtags: Optional[List[str]] = []  # List of hashtags
    mentions: Optional[List[str]] = []  # List of mentioned usernames
    post_url: Optional[str] = None  # Optional URL to include in the post
    start_date: Optional[date | str] = None  # Date when the post should be scheduled
    start_time: Optional[time | str] = None  # Time for scheduling
    end_date: Optional[date | str] = None  # Optional: Date when the post expires
    end_time: Optional[time | str] = None  # Optional: Time when the post expires
    status: PostStatusEnum = Field(
        PostStatusEnum.QUEUED,
        description="Current status of the post (queued, published, etc.)",
    )
    created_date: datetime = Field(
        default_factory=datetime.now, description="Date the post was created"
    )
    last_updated: datetime = Field(
        default_factory=datetime.now, description="Date the post was last updated"
    )

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
            time: lambda v: v.isoformat(),
        }


class SocialMediaPostCreate(SocialMediaPostBase):
    """
    Model for creating a new social media post.
    Inherits from SocialMediaPostBase but ensures date and time fields are normalized.
    """

    # settings: Optional[
    #     Union[
    #         LinkedinSocialMediaPostSettings,
    #         TiktokSocialMediaPostSettings,
    #         FacebookSocialMediaPostSettings,
    #     ]
    # ] = None

    @validator("start_date", pre=True, always=True)
    def validate_date(cls, value):
        # Check if the value is already a valid date object
        if isinstance(value, date):
            return value
        # If the value is a string, attempt to parse it
        if isinstance(value, str):
            try:
                # Try parsing as ISO 8601 datetime and extract the date part
                return datetime.fromisoformat(value).date()
            except ValueError:
                # If parsing fails, raise an error
                raise ValueError(
                    f"Invalid date format: '{value}'. Expected ISO 8601 format or YYYY-MM-DD."
                )
        # If the value is neither a date nor a string, raise an error
        raise ValueError(
            f"Invalid date type: {type(value)}. Expected a string in ISO 8601 or YYYY-MM-DD format or a date object."
        )

    @validator("start_time", pre=True, always=True)
    def validate_time(cls, value):
        # Check if the value is already a valid time object
        if isinstance(value, time):
            return value
        # If the value is a string, attempt to parse it
        if isinstance(value, str):
            try:
                return datetime.strptime(value, "%H:%M:%S").time()
            except ValueError:
                raise ValueError(
                    f"Invalid time format: '{value}'. Expected format is HH:MM:SS."
                )
        # If the value is neither a time nor a string, raise an error
        raise ValueError(
            f"Invalid time type: {type(value)}. Expected a string in HH:MM:SS format or a time object."
        )


class SocialMediaPostUpdate(BaseModel):
    """
    Model for updating a social media post.
    Includes all fields while ensuring date and time fields are validated and normalized.
    """

    post_id: str
    platform: Optional[str] = None
    post_type: Optional[PostTypeEnum] = None
    content: Optional[str] = Field(
        None, max_length=5000, description="Main post content"
    )
    media: Optional[List[MediaItem]] = None  # List of media items
    hashtags: Optional[List[str]] = []  # List of hashtags
    mentions: Optional[List[str]] = []  # List of mentioned usernames
    post_url: Optional[str] = None  # Optional URL to include in the post
    start_date: Optional[date | str] = None  # Date when the post should be scheduled
    start_time: Optional[time | str] = None  # Time for scheduling
    end_date: Optional[date | str] = None  # Optional: Date when the post expires
    end_time: Optional[time | str] = None  # Optional: Time when the post expires
    status: Optional[PostStatusEnum] = None
    last_updated: datetime = Field(
        default_factory=datetime.now, description="Date the post was last updated"
    )

    @validator("start_date", pre=True, always=True)
    def validate_date(cls, value):
        # Check if the value is already a valid date object
        if isinstance(value, date):
            return value
        # If the value is a string, attempt to parse it
        if isinstance(value, str):
            try:
                # Try parsing as ISO 8601 datetime and extract the date part
                return datetime.fromisoformat(value).date()
            except ValueError:
                # If parsing fails, raise an error
                raise ValueError(
                    f"Invalid date format: '{value}'. Expected ISO 8601 format or YYYY-MM-DD."
                )
        # If the value is neither a date nor a string, raise an error
        raise ValueError(
            f"Invalid date type: {type(value)}. Expected a string in ISO 8601 or YYYY-MM-DD format or a date object."
        )

    @validator("start_time", pre=True, always=True)
    def validate_time(cls, value):
        # Check if the value is already a valid time object
        if isinstance(value, time):
            return value
        # If the value is a string, attempt to parse it
        if isinstance(value, str):
            try:
                return datetime.strptime(value, "%H:%M:%S").time()
            except ValueError:
                raise ValueError(
                    f"Invalid time format: '{value}'. Expected format is HH:MM:SS."
                )
        # If the value is neither a time nor a string, raise an error
        raise ValueError(
            f"Invalid time type: {type(value)}. Expected a string in HH:MM:SS format or a time object."
        )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# Full Schema Model
class SocialMediaPost(SocialMediaPostBase):
    """
    Full schema for a social media post, including system-managed fields like ObjectId.
    """

    id: str = Field(
        default_factory=lambda: str(ObjectId()), description="MongoDB ObjectId"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
