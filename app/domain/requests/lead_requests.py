from typing import List, Optional, Union
from pydantic import BaseModel
from app.domain.enums.date_enum import DateFilterEnum
from app.domain.enums.lead_enum import LeadIndustryTypeEnum
from app.domain.enums.leadform_enum import LeadFormTypeEnum
from app.domain.requests.analytics_requests import AnalyticsRequest


class LeadInsightRequest(BaseModel):
    keywords: List[str]  # List of tracked keywords
    search_result: dict  # Raw search result as JSON
    summary: str


# Request model for filtering data
class LeadAnalyticsRequest(AnalyticsRequest):
    lead_type: Optional[LeadFormTypeEnum] = None


class LeadAiReplyContextRequest(BaseModel):
    prompt: str


class GetLeadsByFiltersRequest(BaseModel):
    lead_id: Optional[str] = None
    assigned_to: Optional[str] = None
    lead_status: Optional[str] = None
    interest_level: Optional[str] = None
    lead_source: Optional[str] = None
    starred: Optional[bool] = None
    lead_type: Optional[LeadFormTypeEnum] = None
    lead_form_snapshot_id: Optional[str] = None
    apollo_id: Optional[str] = None
    phone: Optional[str] = None
    is_pre_stored: Optional[bool] = None
    job_title: Optional[str] = None
    location: Optional[str] = None
    company_name: Optional[str] = None
    industry: Optional[LeadIndustryTypeEnum] = None
    emailed: Optional[bool] = None
    called: Optional[bool] = None


class LeadEnrichmentRequest(BaseModel):
    lead_ids: List[str]
    reveal_email: bool = False
    reveal_phone: bool = False
    webhook_url: Optional[str] = None
