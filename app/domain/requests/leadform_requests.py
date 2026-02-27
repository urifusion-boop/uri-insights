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
    monitoring_interval_hours: Optional[int] = 0  # 0 = one-time only, >0 = recurring interval in hours

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
    lead_generation_goal: Optional[str] = None  # User's business goal/reason for generating leads
    monitoring_interval_hours: Optional[int] = 0  # 0 = one-time only, >0 = recurring interval in hours


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


# --- Google Maps Search Form ---
class GoogleMapsSearchFormInput(BaseFormInput):
    form_type: Optional[LeadFormTypeEnum] = LeadFormTypeEnum.GOOGLE_MAPS
    maps_search_mode: Optional[str] = "auto"  # "auto", "text", "nearby"
    maps_search_query: Optional[str] = None  # Natural language query for Text Search
    maps_location: Optional[str] = None  # Location name for Text Search
    maps_latitude: Optional[float] = None  # Latitude for Nearby Search
    maps_longitude: Optional[float] = None  # Longitude for Nearby Search
    maps_radius_km: Optional[float] = None  # Search radius in kilometers
    maps_business_types: Optional[List[str]] = None  # Filter by business types
    maps_min_rating: Optional[float] = None  # Minimum Google rating (0-5)
    maps_exclude_closed: Optional[bool] = True  # Exclude closed businesses
    maps_max_results: Optional[int] = 20  # Maximum results to return


class LeadFormFilterQuery(BaseModel):
    lead_form_id: Optional[str] = None
    user_id: Optional[str] = None
    form_type: Optional[LeadFormTypeEnum] = None
    form_title: Optional[str] = None


class AutoPopulationQuery(BaseModel):
    lead_form_type: LeadFormTypeEnum
    data: Any
