from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from bson import ObjectId
from app.domain.enums.lead_enum import (
    LeadSourceEnum,
    LeadStatusEnum,
    LeadInterestLevelEnum,
    LeadOpportunityTypeEnum,
    LeadIndustryTypeEnum,
)
from app.domain.enums.leadform_enum import LeadFormTypeEnum


# Base Model
class CommunicationEntry(BaseModel):
    date: Optional[datetime] = None
    message: Optional[str] = None
    medium: Optional[str] = None  # e.g., "email", "call", "LinkedIn"
    status: Optional[str] = None  # e.g., "sent", "opened", "responded"


class LeadBase(BaseModel):
    lead_id: str = Field(default_factory=lambda: str(ObjectId()))  # Unique ID
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    keywords: Optional[List[str]] = None
    industry: Optional[LeadIndustryTypeEnum] = LeadIndustryTypeEnum.OTHER
    location: Optional[str] = None
    lead_email: Optional[str] = None
    lead_source: Optional[LeadSourceEnum] = LeadSourceEnum.OTHER
    lead_status: Optional[LeadStatusEnum] = LeadStatusEnum.NEW
    interest_level: Optional[LeadInterestLevelEnum] = LeadInterestLevelEnum.LOW
    assigned_to: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    score: Optional[int] = None
    social_profile: Optional[str] = None
    social_profile_link: Optional[str] = None
    picture_url: Optional[str] = None
    company_logo: Optional[str] = None
    blog_url: Optional[str] = None
    angellist_url: Optional[str] = None
    crunchbase_url: Optional[str] = None
    languages: Optional[List[str]] = None
    founded_year: Optional[int] = None
    primary_domain: Optional[str] = None
    organization_revenue: Optional[int] = None  # In cents or dollars?
    organization_revenue_printed: Optional[str] = None
    organization_headcount_six_month_growth: Optional[int] = None
    organization_headcount_twelve_month_growth: Optional[int] = None
    organization_headcount_twenty_four_month_growth: Optional[int] = None
    linkedin_url: Optional[str] = None
    facebook_url: Optional[str] = None
    twitter_url: Optional[str] = None
    github_url: Optional[str] = None
    website_url: Optional[str] = None
    communication_history: Optional[List[CommunicationEntry]] = None
    campaign_id: Optional[str] = None
    mention: Optional[str] = None
    summary_of_mention: Optional[str] = None
    opportunity_type: Optional[LeadOpportunityTypeEnum] = LeadOpportunityTypeEnum.OTHER
    lead_reason: Optional[str] = None  # Why this lead is relevant
    lead_link: Optional[str] = (
        None  # Link to the lead source (e.g. Google search resultLinkedIn post, Twitter, Facebook, etc.)
    )
    follow_up_message: Optional[str] = None  # Personalized follow-up message
    follow_up_approach: Optional[str] = (
        None  # Best approach for following up (e.g., Email, LinkedIn)
    )
    starred: bool = False
    lead_type: LeadFormTypeEnum = LeadFormTypeEnum.BUSINESS
    emailed: bool = False
    called: bool = False
    lead_files: Optional[List[str]] = None
    lead_form_snapshot_id: Optional[str] = None
    apollo_id: Optional[str] = None
    created_date: datetime = Field(default_factory=datetime.utcnow)  # Creation date
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    is_pre_stored: bool = False

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# Models for CRUD Operations
class LeadCreate(LeadBase):
    """
    Model for creating a new lead.
    Inherits from LeadBase but excludes system-managed fields.
    """

    lead_id: str = Field(default_factory=lambda: str(ObjectId()))


class LeadUpdate(BaseModel):
    """
    Model for updating a lead.
    Excludes system-managed fields.
    """

    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    keywords: Optional[List[str]] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    lead_email: Optional[str] = None
    lead_source: Optional[LeadSourceEnum] = None
    lead_status: Optional[LeadStatusEnum] = None
    interest_level: Optional[LeadInterestLevelEnum] = None
    assigned_to: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    score: Optional[int] = None
    social_profile: Optional[str] = None
    social_profile_link: Optional[str] = None
    picture_url: Optional[str] = None
    company_logo: Optional[str] = None
    linkedin_url: Optional[str] = None
    facebook_url: Optional[str] = None
    twitter_url: Optional[str] = None
    github_url: Optional[str] = None
    communication_history: Optional[List[CommunicationEntry]] = None
    campaign_id: Optional[str] = None
    mention: Optional[str] = None
    summary_of_mention: Optional[str] = None
    lead_files: Optional[List[str]] = None
    opportunity_type: Optional[LeadOpportunityTypeEnum] = None
    lead_reason: Optional[str] = None  # Why this lead is relevant
    follow_up_message: Optional[str] = None  # Personalized follow-up message
    follow_up_approach: Optional[str] = (
        None  # Best approach for following up (e.g., Email, LinkedIn)
    )
    emailed: Optional[bool] = None
    called: Optional[bool] = None
    apollo_id: Optional[str] = None
    is_pre_stored: Optional[bool] = None
    lead_type: Optional[LeadFormTypeEnum] = None

    last_updated: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class Lead(LeadBase):
    """
    Full schema for a lead, including system-managed fields like ObjectId.
    """

    id: str = Field(default_factory=lambda: str(ObjectId()))  # MongoDB ObjectId

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
