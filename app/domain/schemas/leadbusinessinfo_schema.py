from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from bson import ObjectId
from app.core.helpers.date_helper import DateHelper
from app.domain.enums.lead_enum import LeadsProcessedStatus


class LeadSourceSettings(BaseModel):
    max_search_iteration_count: int = 5
    last_scraped_date: Optional[datetime] = None
    last_scraped_status: Optional[LeadsProcessedStatus] = None


class LeadSourceSettingsCreate(BaseModel):
    settings: Optional[LeadSourceSettings] = LeadSourceSettings()


class LeadBusinessInfoBase(BaseModel):
    lead_business_info_id: str = Field(
        default_factory=lambda: str(ObjectId())
    )  # Unique ID
    user_id: str
    business_name: str
    business_summary: str
    business_website: Optional[str] = None
    keywords: Optional[List[str]] = None
    competitors: Optional[List[str]] = None
    source_platforms: Optional[List[str]] = ["google"]
    ai_response_guide: Optional[str] = None
    created_date: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    next_generation_date: datetime = Field(
        default_factory=DateHelper.generate_next_lead_generation_date
    )
    settings: Optional[LeadSourceSettings] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() + "Z" if v else None}


class LeadBusinessInfoCreate(LeadBusinessInfoBase):
    lead_business_info_id: str = Field(
        default_factory=lambda: str(ObjectId())
    )  # Unique ID


class LeadBusinessInfoUpdate(BaseModel):
    business_summary: Optional[str] = None
    business_name: Optional[str] = None
    business_website: Optional[str] = None
    competitors: Optional[List[str]] = None
    source_platforms: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    ai_response_guide: Optional[str] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    settings: Optional[LeadSourceSettings] = None
    next_generation_date: Optional[datetime] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() + "Z" if v else None}


class LeadBusinessInfo(LeadBusinessInfoBase):
    id: str = Field(default_factory=lambda: str(ObjectId()))

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() + "Z" if v else None}
