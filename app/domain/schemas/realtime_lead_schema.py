from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import uuid4
from app.domain.schemas.browsercloud_schema import BrowsercloudPlatformEnum


class RealtimeLeadSource(BaseModel):
    platform: BrowsercloudPlatformEnum
    post_url: str
    post_content: str
    author_name: str
    author_handle: str
    author_url: str
    posted_at: datetime
    engagement_metrics: Optional[dict] = None
    matched_keywords: List[str] = Field(default_factory=list)
    matched_signals: List[str] = Field(default_factory=list)
    raw_data: Optional[dict] = None


class RealtimeLead(BaseModel):
    lead_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    lead_form_id: str
    source: RealtimeLeadSource
    status: str = "new"
    score: Optional[float] = None
    ai_suggested_reply: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_realtime: bool = True
    metadata: Optional[dict] = None

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class RealtimeLeadUpdate(BaseModel):
    status: Optional[str] = None
    score: Optional[float] = None
    ai_suggested_reply: Optional[str] = None
    metadata: Optional[dict] = None


class RealtimeLeadBatch(BaseModel):
    leads: List[RealtimeLead]
    task_id: str
    platform: BrowsercloudPlatformEnum
    processed_at: datetime = Field(default_factory=datetime.utcnow)