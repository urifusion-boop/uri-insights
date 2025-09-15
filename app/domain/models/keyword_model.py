from typing import List, Optional
from pydantic import BaseModel
from app.domain.enums.keyword_enum import AuthorTypeEnum


class AuthorModel(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    type: Optional[AuthorTypeEnum] = None
    link: Optional[str] = None


class PublicMetricsModel(BaseModel):
    retweet_count: Optional[int] = None
    reply_count: Optional[int] = None
    like_count: Optional[int] = None
    quote_count: Optional[int] = None


class SocialMediaPostTrackedItem(BaseModel):
    id: Optional[str] = None
    platform: Optional[str] = None
    title: Optional[str] = None
    text: Optional[str] = None
    htmlTitle: Optional[str] = None
    htmlSnippet: Optional[str] = None
    snippet: Optional[str] = None
    htmlFormattedUrl: Optional[str] = None
    formattedUrl: Optional[str] = None
    displayLink: Optional[str] = None
    link: Optional[str] = None
    pagemap: Optional[dict] = None
    author: Optional[AuthorModel] = None
    public_metrics: Optional[PublicMetricsModel] = None
    timestamp: Optional[str] = None
