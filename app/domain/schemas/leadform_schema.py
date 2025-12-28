from bson import ObjectId
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from app.core.helpers.date_helper import DateHelper
from app.domain.enums.apollo_enum import (
    ContactEmailStatusEnum,
    PersonSenioritiesEnum,
)
from app.domain.enums.leadform_enum import (
    LeadFormDisabledReasonEnum,
    LeadFormTypeEnum,
)
from app.core.helpers.date_helper import DateHelper
from app.domain.enums.lead_enum import LeadsProcessedStatus


class PlatformConfig(BaseModel):
    platform: str
    enabled: bool
    min_followers: Optional[int] = None
    exclude_retweets: Optional[bool] = None
    verified_only: Optional[bool] = None
    content_types: Optional[List[str]] = None

    class Config:
        extra = "forbid"


class LeadSourceSettings(BaseModel):
    max_search_iteration_count: int = 5
    last_scraped_date: Optional[datetime] = None
    last_scraped_status: Optional[LeadsProcessedStatus] = None


class ScoringThresholds(BaseModel):
    """Thresholds for lead qualification scoring"""
    intent_score_min: float = 0.55
    relevance_score_min: float = 0.50
    final_score_min: float = 0.60

    class Config:
        extra = "forbid"


class LeadFormBase(BaseModel):
    lead_form_id: str = Field(default_factory=lambda: str(ObjectId()))
    form_type: LeadFormTypeEnum
    form_title: str
    user_id: str
    disabled: bool = False
    disabled_reason: Optional[LeadFormDisabledReasonEnum] = None
    ai_response_guide: Optional[str] = None
    next_generation_date: datetime = Field(
        default_factory=DateHelper.generate_next_lead_generation_date
    )
    add_to_history: Optional[bool] = True
    auto_generate: Optional[bool] = None
    settings: Optional[LeadSourceSettings] = LeadSourceSettings()

    # Apollo Search Parameters
    # Common Apollo fields
    organization_locations: Optional[List[str]] = None
    organization_ids: Optional[List[str]] = None
    organization_num_employees_ranges: Optional[List[str]] = None

    # Person Search fields
    person_titles: Optional[List[str]] = None
    include_similar_titles: bool = True
    person_locations: Optional[List[str]] = None
    person_seniorities: Optional[List[PersonSenioritiesEnum]] = None
    q_organization_domains_list: Optional[List[str]] = None
    contact_email_status: Optional[List[ContactEmailStatusEnum]] = None
    q_keywords: Optional[str] = None

    # Organization Search fields
    organization_not_locations: Optional[List[str]] = None
    revenue_range_min: Optional[int] = None
    revenue_range_max: Optional[int] = None
    technology_uids: Optional[List[str]] = None
    q_organization_keyword_tags: Optional[List[str]] = None
    q_organization_name: Optional[str] = None

    # Business Form fields (holds some fields for conversational forms as well)
    business_name: Optional[str] = None
    business_summary: Optional[str] = None
    business_website: Optional[str] = None
    source_platforms: Optional[List[str]] = ["google"]

    # Fields common to both conversational and business lead forms
    keywords: Optional[List[str]] = None
    competitors: Optional[List[str]] = None

    # Conversational Form fields
    buying_signals: Optional[List[str]] = None
    excluded_keywords: Optional[List[str]] = None
    location: Optional[List[str]] = None
    intent_type: Optional[str] = None
    post_age_filter: Optional[str] = None  # Time range filter: "24h", "7d", "30d", "3m", "6m", "1y", "all"

    # CLG Upgrade fields - Intent Analysis
    category_context: Optional[str] = None  # Industry/category context (e.g., "skincare", "fintech")
    implied_keywords: Optional[List[str]] = None  # Indirect signals (e.g., "harmattan", "dry skin", "winter")
    scoring_thresholds: Optional[ScoringThresholds] = None  # Custom qualification thresholds

    # V2 Real-time Monitoring fields (for conversational forms)
    enable_realtime: Optional[bool] = False
    monitoring_platforms: Optional[List[str]] = None
    platform_configs: Optional[List[PlatformConfig]] = None
    monitoring_interval_hours: Optional[int] = 0  # 0 = one-time only, >0 = recurring interval in hours (e.g., 1, 2, 3, 6, 12, 24, 48, 72, 120, 168)

    # Job Boards fields
    solution_context: Optional[str] = None  # What problem does user's product/service solve? (for job board analysis)
    job_keywords: Optional[List[str]] = None  # AI-generated job role keywords for job board scanning (PRD Section 5)

    # Pagination
    page: Optional[int] = 1
    per_page: Optional[int] = 10

    # Date fields
    created_date: datetime = Field(default_factory=datetime.utcnow)  # Creation date
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True
        json_encoders = {datetime: lambda v: v.isoformat() + "Z" if v else None}


class LeadFormCreate(LeadFormBase):
    pass


class LeadFormUpdateBase(BaseModel):
    form_title: Optional[str] = None
    form_type: Optional[LeadFormTypeEnum] = None
    disabled: bool = False
    disabled_reason: Optional[LeadFormDisabledReasonEnum] = None
    add_to_history: Optional[bool] = True
    auto_generate: Optional[bool] = None
    # Pagination
    page: Optional[int] = None
    per_page: Optional[int] = None

    class Config:
        use_enum_values = True


class ApolloFormsFields(BaseModel):
    organization_locations: Optional[List[str]] = None
    organization_ids: Optional[List[str]] = None
    organization_num_employees_ranges: Optional[List[str]] = None


class PersonLeadFormUpdate(LeadFormUpdateBase, ApolloFormsFields):
    # Person Search fields
    person_titles: Optional[List[str]] = None
    include_similar_titles: bool = True
    person_locations: Optional[List[str]] = None
    person_seniorities: Optional[List[PersonSenioritiesEnum]] = None
    q_organization_domains_list: Optional[List[str]] = None
    contact_email_status: Optional[List[ContactEmailStatusEnum]] = None
    q_keywords: Optional[str] = None


class OrganizationLeadFormUpdate(LeadFormUpdateBase, ApolloFormsFields):
    # Organization Search fields
    organization_not_locations: Optional[List[str]] = None
    revenue_range_min: Optional[int] = None
    revenue_range_max: Optional[int] = None
    technology_uids: Optional[List[str]] = None
    q_organization_keyword_tags: Optional[List[str]] = None
    q_organization_name: Optional[str] = None


class BizConvLeadFormUpdateBase(LeadFormUpdateBase):
    keywords: Optional[List[str]] = None
    competitors: Optional[List[str]] = None
    ai_response_guide: Optional[str] = None


class BusinessLeadFormUpdate(BizConvLeadFormUpdateBase):
    # Business Form fields
    business_name: Optional[str] = None
    business_summary: Optional[str] = None
    business_website: Optional[str] = None
    source_platforms: Optional[List[str]] = ["google"]
    next_generation_date: datetime = Field(
        default_factory=DateHelper.generate_next_lead_generation_date
    )
    settings: Optional[LeadSourceSettings] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() + "Z" if v else None}


class ConversationalLeadFormUpdate(BizConvLeadFormUpdateBase):
    # Conversational Form fields
    buying_signals: Optional[List[str]] = None
    excluded_keywords: Optional[List[str]] = None
    location: Optional[List[str]] = None
    intent_type: Optional[str] = None
    post_age_filter: Optional[str] = None  # Time range filter: "24h", "7d", "30d", "3m", "6m", "1y", "all"

    # CLG Upgrade fields - Intent Analysis
    category_context: Optional[str] = None  # Industry/category context (e.g., "skincare", "fintech")
    implied_keywords: Optional[List[str]] = None  # Indirect signals (e.g., "harmattan", "dry skin", "winter")
    scoring_thresholds: Optional[ScoringThresholds] = None  # Custom qualification thresholds

    # V2 Real-time Monitoring fields
    enable_realtime: Optional[bool] = None
    monitoring_platforms: Optional[List[str]] = None
    platform_configs: Optional[List[PlatformConfig]] = None
    monitoring_interval_hours: Optional[int] = None  # 0 = one-time only, >0 = recurring interval in hours

    # Job Boards fields
    solution_context: Optional[str] = None  # What problem does user's product/service solve?
    job_keywords: Optional[List[str]] = None  # AI-generated job role keywords (PRD Section 5)


class LeadForm(LeadFormBase):
    id: str = Field(default_factory=lambda: str(ObjectId()))

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() + "Z" if v else None}
