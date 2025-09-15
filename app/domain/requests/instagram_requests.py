from datetime import datetime
from typing import List, Dict, Optional
from pydantic import BaseModel

from app.domain.enums.instagram_enum import InstagramMediaTypeEnum


class InstagramInsightsRequest(BaseModel):
    influencer_id: str
    access_token: str
    metrics: str
    period: str
    since: Optional[str] = None
    until: Optional[str] = None


class CommentSentimentRequest(BaseModel):
    comments: List[Dict]


class PostSummaryRequest(BaseModel):
    posts: List[dict]


class PostInstagramMediaRequest(BaseModel):
    media_url: str
    media_type: InstagramMediaTypeEnum
    caption: str


class InstagramInsightsParameters(BaseModel):
    instagram_user_id: Optional[str]
    metrics: Optional[str]
    metric_type: Optional[str]
    period: Optional[str] = "day"
    user_facebook_access_token: str
    since: Optional[str | datetime] = None
    until: Optional[str | datetime] = None
