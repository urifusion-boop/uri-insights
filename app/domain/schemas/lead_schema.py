from typing import Optional, List, Union, Any
from datetime import datetime
from pydantic import BaseModel, Field
from app.core.helpers.date_helper import DateHelper
from bson import ObjectId
from app.domain.enums.lead_enum import (
    LeadSourceEnum,
    LeadStatusEnum,
    LeadInterestLevelEnum,
    LeadOpportunityTypeEnum,
    LeadIndustryTypeEnum,
    IntentCategoryEnum,
    SentimentTypeEnum,
)
from app.domain.enums.leadform_enum import LeadFormTypeEnum


# Base Model
class CommunicationEntry(BaseModel):
    date: Optional[datetime] = None
    message: Optional[str] = None
    medium: Optional[str] = None  # e.g., "email", "call", "LinkedIn"
    status: Optional[str] = None  # e.g., "sent", "opened", "responded"

    class Config:
        extra = "forbid"


class AINextSteps(BaseModel):
    """For reading from database - flexible to handle old data formats"""
    steps: Optional[Union[List[str], List[dict], List[Any]]] = None  # Support both string lists and complex objects
    generated_at: Optional[str] = None
    based_on_goal: Optional[str] = None
    summary: Optional[str] = None

    class Config:
        extra = "allow"  # Allow extra fields for backward compatibility with existing data


class AINextStepsStrict(BaseModel):
    """For OpenAI structured output - strict validation"""
    steps: Optional[List[str]] = None
    generated_at: Optional[str] = None
    based_on_goal: Optional[str] = None
    summary: Optional[str] = None

    class Config:
        extra = "forbid"


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

    # CLG Upgrade - Intent Analysis Fields
    intent_score: Optional[float] = None  # How strong is the buying intent (0-1)
    relevance_score: Optional[float] = None  # How relevant to the product/service (0-1)
    urgency_flag: Optional[bool] = None  # Is there urgency in the post?
    sentiment: Optional[SentimentTypeEnum] = None  # Overall sentiment (positive/negative/neutral)
    intent_category: Optional[IntentCategoryEnum] = None  # Type of intent detected
    final_score: Optional[float] = None  # Combined qualification score (0-1)
    intent_reasoning: Optional[str] = None  # Brief explanation of intent analysis
    content_hash: Optional[str] = None  # Hash of normalized content to detect retweets/shares

    # Job Signal Fields (for leads from job boards)
    job_posting_url: Optional[str] = None  # URL to the job posting
    job_title_field: Optional[str] = None  # Job title from posting (renamed to avoid conflict with job_title)
    hiring_company: Optional[str] = None  # Company posting the job
    problem_solution_match: Optional[float] = None  # Score: How well user's solution addresses the hiring problem (0-1)
    hiring_intent_score: Optional[float] = None  # Score: How urgent/serious is the hiring need (0-1)
    commercial_relevance: Optional[float] = None  # Score: Calculated from problem_match + hiring_intent (0-1)
    implied_problems: Optional[List[str]] = None  # AI-generated list of business problems this hiring suggests
    job_source: Optional[str] = None  # Source of job posting: "LinkedIn Jobs", "Jobberman"
    company_confidence: Optional[float] = None  # PRD Sections 14-16: Confidence that company can be verified (0-1)

    # AI Next Steps - Actionable recommendations based on user's goal
    ai_next_steps: Optional[AINextSteps] = None

    # Form Title - Populated from lead_form_snapshots via aggregation
    form_title: Optional[str] = None  # Form title from the snapshot that generated this lead

    # Lazarus Protocol - Resurrection tracking fields
    is_lazarus_monitored: Optional[bool] = False  # Is this lead being monitored by Lazarus?
    lazarus_focus_id: Optional[str] = None  # Link to focus_contacts collection
    lazarus_company_monitor_id: Optional[str] = None  # Link to company_monitors collection
    resurrection_count: Optional[int] = 0  # How many times has this lead been resurrected?
    last_resurrection_date: Optional[datetime] = None  # When was the last resurrection?
    last_resurrection_type: Optional[str] = None  # Type of alert that triggered resurrection
    marked_dead_date: Optional[datetime] = None  # When was this lead marked as DEAD?
    marked_dead_reason: Optional[str] = None  # Why was this lead marked as DEAD?

    class Config:
        json_encoders = {datetime: lambda v: DateHelper.to_iso8601_utc(v) if v else None}


# Models for CRUD Operations
class LeadCreate(LeadBase):
    """
    Model for creating a new lead.
    Inherits from LeadBase but excludes system-managed fields.
    """

    lead_id: str = Field(default_factory=lambda: str(ObjectId()))
    ai_next_steps: Optional[AINextStepsStrict] = None  # Override with strict version for OpenAI

    class Config:
        extra = "forbid"  # Only for OpenAI structured output validation
        json_encoders = {datetime: lambda v: DateHelper.to_iso8601_utc(v) if v else None}


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

    # CLG Upgrade - Intent Analysis Fields (for updates)
    intent_score: Optional[float] = None
    relevance_score: Optional[float] = None
    urgency_flag: Optional[bool] = None
    sentiment: Optional[SentimentTypeEnum] = None
    intent_category: Optional[IntentCategoryEnum] = None
    final_score: Optional[float] = None
    intent_reasoning: Optional[str] = None

    # Job Signal Fields (for updates)
    job_posting_url: Optional[str] = None
    job_title_field: Optional[str] = None
    hiring_company: Optional[str] = None
    problem_solution_match: Optional[float] = None
    hiring_intent_score: Optional[float] = None
    commercial_relevance: Optional[float] = None
    implied_problems: Optional[List[str]] = None
    job_source: Optional[str] = None
    company_confidence: Optional[float] = None

    # AI Next Steps (for updates)
    ai_next_steps: Optional[AINextSteps] = None

    last_updated: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: DateHelper.to_iso8601_utc(v) if v else None}


class Lead(LeadBase):
    """
    Full schema for a lead, including system-managed fields like ObjectId.
    """

    id: str = Field(default_factory=lambda: str(ObjectId()))  # MongoDB ObjectId

    class Config:
        json_encoders = {datetime: lambda v: DateHelper.to_iso8601_utc(v) if v else None}
