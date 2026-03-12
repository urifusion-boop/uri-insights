# app/agents/social_media_manager/schemas/content_schemas.py

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class SeedType(str, Enum):
    """Types of seed content for generation"""
    TEXT = "text"
    URL = "url" 
    IMAGE = "image"
    MENTION_RESPONSE = "mention_response"
    TREND_ANALYSIS = "trend_analysis"


class Platform(str, Enum):
    """Supported social media platforms"""
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    FACEBOOK = "facebook" 
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"


class ContentStatus(str, Enum):
    """Status of content throughout the workflow"""
    GENERATING = "generating"
    READY = "ready"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"


class BrandContext(BaseModel):
    """Brand information for personalizing AI-generated content"""
    brand_name: Optional[str] = Field(None, max_length=100, description="Business or brand name")
    brand_colors: Optional[List[str]] = Field(None, max_items=10, description="Brand colors as hex codes or names e.g. ['#FF5733', 'navy blue']")
    brand_voice: Optional[str] = Field(None, max_length=500, description="Brand tone/voice e.g. 'professional and witty'")
    target_audience: Optional[str] = Field(None, max_length=500, description="Who the content is aimed at")
    business_description: Optional[str] = Field(None, max_length=1000, description="Short description of what the business does")
    tagline: Optional[str] = Field(None, max_length=200, description="Brand tagline or slogan")
    industry: Optional[str] = Field(None, max_length=100, description="Industry or sector")
    key_products_services: Optional[List[str]] = Field(None, max_items=10, description="Main products or services to highlight")


class ContentGenerationRequest(BaseModel):
    """
    Request schema for generating multi-platform content
    """
    seed_content: str = Field(..., min_length=10, max_length=5000, description="Original content to transform")
    platforms: List[Platform] = Field(..., min_items=1, max_items=5, description="Platforms to generate content for")
    seed_type: SeedType = Field(default=SeedType.TEXT, description="Type of seed content")
    brand_context: Optional[BrandContext] = Field(None, description="Brand information to personalize the generated content")
    
    @validator('seed_content')
    def validate_seed_content(cls, v):
        if not v.strip():
            raise ValueError('Seed content cannot be empty')
        return v.strip()
    
    @validator('platforms')
    def validate_platforms(cls, v):
        if not v:
            raise ValueError('At least one platform must be specified')
        # Remove duplicates while preserving order
        seen = set()
        unique_platforms = []
        for platform in v:
            if platform not in seen:
                seen.add(platform)
                unique_platforms.append(platform)
        return unique_platforms
    
    class Config:
        use_enum_values = True


class AIMetadata(BaseModel):
    """AI generation metadata for tracking"""
    model_used: str
    prompt_version: str
    generation_time: str
    temperature: float
    platform: str
    seed_length: int
    output_length: int
    hashtag_count: int
    nigerian_context: bool = True


class ContentDraft(BaseModel):
    """Individual content draft for a specific platform"""
    id: str
    platform: Platform
    content: str
    original_content: str
    hashtags: List[str] = []
    word_count: int
    ai_metadata: AIMetadata
    is_twitter_thread: bool = False
    tweets: Optional[List[str]] = None
    
    class Config:
        use_enum_values = True


class ContentDraftResponse(BaseModel):
    """Response schema for generated content drafts"""
    request_id: str
    seed_content: str
    seed_type: SeedType
    requested_platforms: List[Platform]
    successful_platforms: List[Platform]
    drafts: List[ContentDraft]
    errors: List[Dict[str, str]] = []
    status: ContentStatus
    generated_at: str
    
    class Config:
        use_enum_values = True


class ContentRequestResponse(BaseModel):
    """Response schema for content requests"""
    id: str
    user_id: str
    seed_content: str
    seed_type: SeedType
    requested_platforms: List[Platform]
    status: ContentStatus
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        use_enum_values = True


class PlatformRequirements(BaseModel):
    """Platform-specific content requirements"""
    platform: Platform
    max_length: int
    optimal_length: int
    tone: str
    format: str
    hashtag_limit: int
    audience: str
    context: str
    
    class Config:
        use_enum_values = True


class ContentRegenerationRequest(BaseModel):
    """Request to regenerate content with feedback"""
    draft_id: str
    feedback: Optional[str] = Field(None, max_length=500, description="Optional feedback to improve content")
    
    @validator('feedback')
    def validate_feedback(cls, v):
        if v is not None and not v.strip():
            return None
        return v.strip() if v else None


class ScheduleRequest(BaseModel):
    """Request to schedule content for publishing"""
    draft_id: str
    publish_immediately: bool = False
    scheduled_date: Optional[datetime] = None
    
    @validator('scheduled_date')
    def validate_scheduled_date(cls, v, values):
        if not values.get('publish_immediately', False) and v is None:
            raise ValueError('Scheduled date required when not publishing immediately')
        if v and v <= datetime.utcnow():
            raise ValueError('Scheduled date must be in the future')
        return v


class DraftUpdateRequest(BaseModel):
    """Request to update a content draft"""
    content: Optional[str] = Field(None, min_length=10, max_length=5000)
    hashtags: Optional[List[str]] = Field(None, max_items=20)
    media_urls: Optional[List[str]] = None
    
    @validator('hashtags')
    def validate_hashtags(cls, v):
        if v is not None:
            # Clean hashtags and remove duplicates
            cleaned = []
            seen = set()
            for tag in v:
                clean_tag = tag.strip().replace('#', '').replace(' ', '')
                if clean_tag and clean_tag.lower() not in seen:
                    seen.add(clean_tag.lower())
                    cleaned.append(clean_tag)
            return cleaned[:15]  # Limit to 15 hashtags
        return v


class PublishingResult(BaseModel):
    """Result of content publishing"""
    draft_id: str
    platform: Platform
    success: bool
    platform_post_id: Optional[str] = None
    error_message: Optional[str] = None
    published_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True


class AnalyticsData(BaseModel):
    """Analytics data for published content"""
    views: int = 0
    likes: int = 0
    shares: int = 0
    comments: int = 0
    clicks: int = 0
    saves: int = 0
    engagement_rate: float = 0.0
    click_through_rate: float = 0.0


class ContentAnalytics(BaseModel):
    """Complete analytics for a content piece"""
    draft_id: str
    platform_post_id: Optional[str] = None
    analytics: AnalyticsData
    peak_engagement_hour: Optional[int] = None
    last_updated: Optional[datetime] = None
    data_freshness: str = "real_time"