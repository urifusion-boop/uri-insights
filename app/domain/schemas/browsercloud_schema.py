from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import uuid4


class BrowsercloudPlatformEnum(str, Enum):
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"
    THREADS = "threads"


class BrowsercloudTaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BrowsercloudSocialPost(BaseModel):
    platform: BrowsercloudPlatformEnum
    post_id: str
    content: str
    url: str
    author_name: str
    author_handle: str
    author_url: str
    posted_at: datetime
    engagement_metrics: Optional[dict] = None
    matched_keywords: List[str] = Field(default_factory=list)
    matched_signals: List[str] = Field(default_factory=list)


class BrowsercloudTaskCreate(BaseModel):
    platform: BrowsercloudPlatformEnum
    keywords: List[str]
    buying_signals: List[str]
    excluded_keywords: Optional[List[str]] = None
    location: Optional[str] = None
    webhook_url: str
    task_id: str = Field(default_factory=lambda: str(uuid4()))


class BrowsercloudTaskResponse(BaseModel):
    task_id: str
    status: BrowsercloudTaskStatus
    created_at: datetime
    updated_at: datetime
    platform: BrowsercloudPlatformEnum
    results: List[BrowsercloudSocialPost] = Field(default_factory=list)
    error: Optional[str] = None