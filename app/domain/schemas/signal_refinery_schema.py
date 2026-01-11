"""
Signal Refinery Schema - Google X-Ray Method Testing System

This is a SEPARATE testing system for the "Signal Refinery" architecture:
- Google X-Ray search (site: dork queries)
- Pre-filtering (blocklist, bot detection)
- Buyer/Seller LLM classification
- Cost comparison vs traditional scrapers

Does NOT touch existing conversational lead system.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from bson import ObjectId
from enum import Enum


class XRayPlatformEnum(str, Enum):
    """Platforms supported for X-Ray search"""
    TWITTER = "Twitter"
    NAIRALAND = "Nairaland"
    LINKEDIN = "LinkedIn"
    REDDIT = "Reddit"


class FilterReasonEnum(str, Enum):
    """Reasons for filtering out signals"""
    BLOCKLIST = "blocklist"  # Matched spam keywords (crypto, forex, etc.)
    BOT_PATTERN = "bot_pattern"  # Matched bot patterns (dm for rates, click link)
    NOT_NIGERIAN = "not_nigerian"  # Failed Nigerian entity check
    SELLER = "seller"  # LLM classified as seller, not buyer
    NO_INTENT = "no_intent"  # No buying intent detected
    DUPLICATE = "duplicate"  # Duplicate content


class BuyerSellerEnum(str, Enum):
    """LLM classification of signal"""
    BUYER = "buyer"  # Someone needing a product/service
    SELLER = "seller"  # Someone advertising/promoting
    UNKNOWN = "unknown"  # Cannot determine


# ========================================
# REQUEST MODELS
# ========================================

class XRaySearchRequest(BaseModel):
    """Request model for X-Ray search"""
    user_id: str
    keyword: str  # Main search keyword
    platforms: List[XRayPlatformEnum]  # Which platforms to search
    location: str = "Nigeria"  # Default to Nigeria
    max_results_per_platform: int = 50  # Max results per platform
    enable_buyer_seller_classification: bool = True  # Run LLM buyer/seller check
    enable_nigerian_filter: bool = True  # Filter for Nigerian entities
    compare_with_traditional: bool = False  # Run side-by-side comparison


# ========================================
# RESULT MODELS
# ========================================

class XRaySearchResult(BaseModel):
    """Single search result from Google X-Ray"""
    result_id: str = Field(default_factory=lambda: str(ObjectId()))
    platform: XRayPlatformEnum
    title: str
    snippet: str  # Text preview from Google
    url: str
    source_date: Optional[datetime] = None  # When original post was created
    google_rank: Optional[int] = None  # Position in Google results (1-100)

    # Dork query that found this result
    dork_query: str

    # Raw data from Apify
    raw_data: Optional[Dict[str, Any]] = None


class FilteredResult(BaseModel):
    """Result that was filtered out (for analysis)"""
    result: XRaySearchResult
    filter_reason: FilterReasonEnum
    filter_detail: str  # Specific reason (e.g., "Matched blocklist: crypto")


class BuyerSellerClassification(BaseModel):
    """LLM classification result"""
    classification: BuyerSellerEnum
    confidence: float = Field(ge=0, le=1)  # 0-1 confidence score
    reasoning: str  # Why LLM classified this way
    pain_point: Optional[str] = None  # If buyer, what's their pain?
    product_needed: Optional[str] = None  # If buyer, what do they need?


class XRayLead(BaseModel):
    """Final lead after all filtering (buyer signals only)"""
    lead_id: str = Field(default_factory=lambda: str(ObjectId()))
    user_id: str

    # Source data
    platform: XRayPlatformEnum
    title: str
    snippet: str
    url: str
    full_text: Optional[str] = None  # If we fetch full content

    # Search context
    search_keyword: str
    location: str
    dork_query: str

    # Classification
    buyer_seller: BuyerSellerClassification

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    google_rank: Optional[int] = None

    # Filters passed
    passed_blocklist: bool = True
    passed_bot_detection: bool = True
    passed_nigerian_check: bool = True

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


# ========================================
# METRICS & COMPARISON
# ========================================

class RefineryMetrics(BaseModel):
    """Metrics for X-Ray search vs traditional scraping"""

    # Volume
    total_fetched: int  # Total results from Google
    blocklist_filtered: int  # Removed by keyword blocklist
    bot_filtered: int  # Removed by bot pattern detection
    nigerian_filtered: int  # Removed by Nigerian entity check
    seller_filtered: int  # Classified as sellers by LLM
    duplicate_filtered: int  # Duplicate content
    final_buyer_count: int  # Final buyer leads

    # Quality
    buyer_seller_ratio: float  # Buyers / Total
    spam_ratio: float  # Filtered / Total

    # Cost (in USD)
    google_search_cost: float  # Apify Google scraper cost
    llm_classification_cost: float  # OpenAI cost for buyer/seller
    total_cost: float
    cost_per_lead: float  # Total cost / final_buyer_count

    # Performance
    total_time_seconds: float
    leads_per_second: float

    # Comparison (if compare_with_traditional = True)
    traditional_scraper_cost: Optional[float] = None
    traditional_spam_ratio: Optional[float] = None
    cost_savings_percent: Optional[float] = None
    quality_improvement_percent: Optional[float] = None


class XRaySearchJob(BaseModel):
    """Job tracking for async X-Ray search"""
    job_id: str = Field(default_factory=lambda: str(ObjectId()))
    user_id: str
    request: XRaySearchRequest

    # Status
    status: str  # "running", "completed", "failed"
    progress: int = 0  # 0-100
    current_step: str = ""  # What's happening now

    # Results
    results: List[XRaySearchResult] = []
    filtered: List[FilteredResult] = []
    leads: List[XRayLead] = []
    metrics: Optional[RefineryMetrics] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Error handling
    error_message: Optional[str] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


# ========================================
# RESPONSE MODELS
# ========================================

class XRaySearchResponse(BaseModel):
    """Response from starting X-Ray search"""
    success: bool
    job_id: str
    message: str


class XRayJobStatusResponse(BaseModel):
    """Response for job status check"""
    success: bool
    job: XRaySearchJob


class DorkQueryPreview(BaseModel):
    """Preview of dork query that will be used"""
    platform: XRayPlatformEnum
    query: str
    estimated_results: Optional[int] = None
