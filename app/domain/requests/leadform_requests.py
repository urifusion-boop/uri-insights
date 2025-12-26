from pydantic import BaseModel, Field
from typing import Any, Optional, List
from app.domain.enums.leadform_enum import (
    LeadFormTypeEnum,
)
from app.domain.requests.apollo_requests import (
    OrganizationSearchRequest,
    PersonSearchRequest,
)
from app.domain.schemas.leadform_schema import PlatformConfig, ScoringThresholds


class BaseBusinessAndConversationalSearchRequest(BaseModel):
    keywords: Optional[List[str]] = None
    competitors: Optional[List[str]] = None
    ai_response_guide: Optional[str] = None


class BusinessSearchRequest(BaseBusinessAndConversationalSearchRequest):
    business_name: str
    business_summary: str
    business_website: Optional[str] = None

    class Config:
        use_enum_values = True
        validate_assignment = True
        populate_by_name = True  # Allows using aliases
        json_schema_extra = {
            "example": {
                "business_name": "Tech Company",
                "business_summary": "Tech Company is a tech company that makes tech products.",
                "business_website": "https://www.techcompany.com",
                "keywords": ["tech", "company", "products"],
                "competitors": ["Google", "Apple", "Microsoft"],
                "ai_response_guide": "AI response guide",
            }
        }


class ConversationalSearchRequest(BaseBusinessAndConversationalSearchRequest):
    buying_signals: Optional[List[str]] = None
    excluded_keywords: Optional[List[str]] = None
    intent_type: Optional[str] = None
    location: Optional[List[str]] = None  # Changed from str to List[str] for geographic filtering
    post_age_filter: Optional[str] = "all"  # Time range filter: "24h", "7d", "30d", "3m", "6m", "1y", "all"

    # CLG Upgrade fields - Intent Analysis
    category_context: Optional[str] = None  # Industry/category context (e.g., "skincare", "fintech")
    implied_keywords: Optional[List[str]] = None  # Indirect signals (e.g., "harmattan", "dry skin", "winter")
    scoring_thresholds: Optional[ScoringThresholds] = None  # Custom qualification thresholds

    # V2 Real-time Monitoring fields
    enable_realtime: Optional[bool] = False
    monitoring_platforms: Optional[List[str]] = None
    platform_configs: Optional[List[PlatformConfig]] = None

    # Job Boards fields (PRD Section 5) - Only for Conversational forms
    solution_context: Optional[str] = None  # What problem does user's product/service solve?
    job_keywords: Optional[List[str]] = None  # AI-generated job role keywords for job board scanning


# --- Base Form Input ---
class BaseFormInput(BaseModel):
    form_title: str = Field(
        ..., description="The name of the form provided by the user."
    )
    user_id: str = Field(...)
    add_to_history: Optional[bool] = None
    auto_generate: Optional[bool] = None


# --- Person Search Form ---
class PersonSearchFormInput(BaseFormInput, PersonSearchRequest):
    form_type: Optional[LeadFormTypeEnum] = LeadFormTypeEnum.PERSON


# --- Organization Search Form ---
class OrganizationSearchFormInput(BaseFormInput, OrganizationSearchRequest):
    form_type: Optional[LeadFormTypeEnum] = LeadFormTypeEnum.ORGANIZATION
    technology_uids: Optional[List[str]] = None


# --- Business Search Form ---
class BusinessSearchFormInput(BaseFormInput, BusinessSearchRequest):
    form_type: Optional[LeadFormTypeEnum] = LeadFormTypeEnum.BUSINESS


# --- Conversational Search Form ---
class ConversationalSearchFormInput(BaseFormInput, ConversationalSearchRequest):
    form_type: Optional[LeadFormTypeEnum] = LeadFormTypeEnum.CONVERSATIONAL


class LeadFormFilterQuery(BaseModel):
    lead_form_id: Optional[str] = None
    user_id: Optional[str] = None
    form_type: Optional[LeadFormTypeEnum] = None
    form_title: Optional[str] = None


class AutoPopulationQuery(BaseModel):
    lead_form_type: LeadFormTypeEnum
    data: Any
