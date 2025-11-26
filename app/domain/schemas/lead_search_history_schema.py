"""
Lead Search History Schema
Tracks conversational lead search operations for analytics and preventing duplicate searches
"""
from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel, Field
from bson import ObjectId


class SearchResultStats(BaseModel):
    """Statistics from a lead search operation"""
    total_fetched: int = 0  # Total posts found across platforms
    total_qualified: int = 0  # Posts that passed intent analysis
    new_leads_saved: int = 0  # New leads added to database
    duplicates_skipped: int = 0  # Leads that already existed


class LeadSearchHistoryBase(BaseModel):
    """Base model for lead search history"""
    user_id: str
    lead_form_id: str
    lead_form_name: Optional[str] = None
    keyword: str  # The search keyword used
    platforms: List[str] = Field(default_factory=list)  # Platforms searched (twitter, facebook, tiktok)
    search_timestamp: datetime = Field(default_factory=datetime.utcnow)
    results: SearchResultStats
    duration_seconds: Optional[float] = None  # How long the search took
    success: bool = True  # Whether the search completed successfully
    error_message: Optional[str] = None  # Error if search failed

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z" if v else None
        }


class LeadSearchHistoryCreate(LeadSearchHistoryBase):
    """Model for creating search history"""
    pass


class LeadSearchHistory(LeadSearchHistoryBase):
    """Full search history model with database fields"""
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z" if v else None
        }


class LeadSearchHistorySummary(BaseModel):
    """Summary statistics for a lead form's search history"""
    lead_form_id: str
    lead_form_name: Optional[str] = None
    total_searches: int
    total_leads_found: int
    total_duplicates_skipped: int
    last_search_timestamp: Optional[datetime] = None
    most_used_keyword: Optional[str] = None
    average_leads_per_search: float = 0.0

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z" if v else None
        }
