from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from bson import ObjectId

from app.domain.enums.socialmediapost_enum import PostPlatformEnum
from ..enums.account_enum import AccountTypeEnum


class InfluencerBase(BaseModel):
    user_id: str
    social_user_id: Optional[str] = None
    social_username: Optional[str] = None
    social_name: Optional[str] = None
    profile_pic: Optional[str] = None
    social_platform: Optional[PostPlatformEnum] = None
    account_type: Optional[AccountTypeEnum] = None
    email: Optional[str] = None
    tags: Optional[List[str]] = None
    profile_image: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    followers: Optional[int] = None
    token: Optional[str | dict] = None
    meta_access_token: Optional[str] = None
    instagram_access_token: Optional[str] = None
    facebook_access_token: Optional[str] = None
    linkedin_access_token: Optional[str] = None
    twitter_access_token: Optional[str] = None
    tiktok_access_token: Optional[str] = None 
    connected: Optional[bool] = None
    createdAt: Optional[datetime] = datetime.now()
    updatedAt: Optional[datetime] = datetime.now()

    class Config:
        from_attributes = True


class InfluencerCreate(InfluencerBase):
    pass


class InfluencerUpdate(BaseModel):
    influencer_id: str
    user_id: str
    social_user_id: Optional[str] = None
    social_username: Optional[str] = None
    social_name: Optional[str] = None
    profile_pic: Optional[str] = None
    account_type: Optional[AccountTypeEnum] = None
    email: Optional[str] = None
    tags: Optional[List[str]] = None
    profile_image: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    followers: Optional[int] = None
    token: Optional[str] = None
    connected: Optional[bool] = None
    updatedAt: Optional[datetime] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() + "Z" if v else None}


class Influencer(InfluencerBase):
    influencer_id: str
    id: str = Field(default_factory=lambda: str(ObjectId()))

    class Config:
        from_attributes = True
