"""
Spam Lead Schema - For analyzed but unqualified items (PRD Section 3.2)

Spam = Analyzed but Unqualified Items
These are real posts/jobs that were analyzed but did not meet qualification criteria.

Applies to:
- Sales Signals (Job Boards): Failed commercial_relevance threshold
- Social Media Posts: Failed intent analysis threshold

PRD Reference: Lead Gen Enhancement PRD - Spam Visibility Feature
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from bson import ObjectId


class SpamLeadBase(BaseModel):
    """
    Complete schema for spam leads (unqualified but analyzed items)

    Applies to BOTH:
    - Sales Signals (Job Boards) - Failed AI analysis
    - Social Media Posts (X, Reddit, Facebook, TikTok) - Failed intent analysis

    PRD Section 3.2: "Spam = Analyzed but Unqualified Items"
    """

    # === IDENTITY ===
    spam_id: str = Field(default_factory=lambda: str(ObjectId()))
    user_id: str  # Who ran the search

    # === COMPLETE ORIGINAL LEAD DATA ===
    # Store entire LeadCreate object as dict for full preservation
    # Allows promotion back to qualified leads with all original data intact
    original_lead_data: Dict[str, Any]

    # === SPAM CLASSIFICATION ===
    spam_reason: str  # Primary reason (use SpamReasonEnum values)
    spam_reason_detail: Optional[str] = None  # Additional explanation with scores
    spam_timestamp: datetime = Field(default_factory=datetime.utcnow)
    filter_stage: str  # "job_board_ai" | "intent_analysis" | "time_filter" | "location_filter" | "duplicate"

    # === LEAD SOURCE CONTEXT ===
    lead_source: str  # "Job Boards", "X", "Reddit", "Facebook", "TikTok", etc.
    platform_detail: Optional[str] = None  # "LinkedIn Jobs", "Jobberman", "Indeed" for job boards

    # ========================================
    # JOB BOARD FIELDS (for Sales Signals)
    # Only populated when lead_source = "Job Boards"
    # ========================================

    # Job Board AI Scores (why it failed)
    problem_solution_match: Optional[float] = None  # 0-1: How well solution addresses hiring problem
    hiring_intent_score: Optional[float] = None     # 0-1: How urgent is the hiring need
    commercial_relevance: Optional[float] = None    # 0-1: Calculated (0.6 * problem_match) + (0.4 * hiring_intent)
    company_confidence: Optional[float] = None      # 0-1: Confidence company can be verified

    # Job Board Thresholds
    commercial_relevance_threshold: Optional[float] = None  # Usually 0.3

    # Job Board AI Results
    implied_problems: Optional[List[str]] = None      # Business problems this hiring suggests
    target_seniorities: Optional[List[str]] = None    # Who to contact (CTO, VP, etc.)
    job_board_reasoning: Optional[str] = None         # AI explanation for job analysis

    # Job Specific Fields
    job_posting_url: Optional[str] = None
    job_title: Optional[str] = None
    hiring_company: Optional[str] = None
    job_source: Optional[str] = None  # "LinkedIn Jobs", "Jobberman", "Indeed"

    # ========================================
    # SOCIAL POST FIELDS (for Social Media)
    # Only populated when lead_source = X, Reddit, Facebook, etc.
    # ========================================

    # Intent Analysis Scores (why it failed)
    intent_score: Optional[float] = None              # 0-1: How strong is buying intent
    relevance_score: Optional[float] = None           # 0-1: How relevant to business category
    final_score: Optional[float] = None               # 0-1: Combined score
    urgency_flag: Optional[bool] = None               # Is there urgency in post
    sentiment: Optional[str] = None                   # "positive" | "negative" | "neutral"
    intent_category: Optional[str] = None             # "direct" | "implied" | "problem" | "comparison" | etc.
    intent_reasoning: Optional[str] = None            # AI explanation for intent analysis

    # Intent Analysis Thresholds
    intent_min_threshold: Optional[float] = None      # Usually 0.50
    relevance_min_threshold: Optional[float] = None   # Usually 0.45
    final_min_threshold: Optional[float] = None       # Usually 0.55

    # Social Post Specific
    post_author: Optional[str] = None       # Username/author
    post_url: Optional[str] = None          # Link to original post
    social_profile: Optional[str] = None    # Profile URL

    # ========================================
    # COMMON FIELDS (Both Job Boards & Social)
    # ========================================

    # Search Context (how this was found)
    search_keyword: str                               # Keyword that fetched this
    search_category: Optional[str] = None             # Business category context
    category_keywords: Optional[List[str]] = None     # All keywords from category config
    buying_signals: Optional[List[str]] = None        # Buying signals used in search
    excluded_keywords: Optional[List[str]] = None     # Keywords that were excluded
    solution_context: Optional[str] = None            # User's solution description (for job boards)

    # Campaign/Form Context (PRD 4.7: Spam scoped per form)
    lead_form_snapshot_id: str  # REQUIRED: Each form has its own spam list
    campaign_id: Optional[str] = None

    # Time Filter Context (if filtered by time)
    post_age_filter: Optional[str] = None             # "24h", "7d", "30d", "3m", "6m", "1y", "all"
    cutoff_date: Optional[datetime] = None            # Calculated cutoff date
    post_created_date: Optional[datetime] = None      # When post/job was originally created

    # Location Filter Context (if filtered by location)
    target_locations: Optional[List[str]] = None      # Target locations from form
    post_location: Optional[str] = None               # Detected location in post/job

    # Content (for both posts and jobs)
    content_preview: Optional[str] = None             # First 300 chars for quick view
    content_full: Optional[str] = None                # Complete post/job description text

    # ========================================
    # QUICK ACCESS FIELDS (UI Display - PRD Section 3.4)
    # Populated for fast UI rendering without parsing original_lead_data
    # ========================================
    display_title: Optional[str] = None       # Job title OR post first 100 chars
    display_company: Optional[str] = None     # Company name (jobs) OR empty (posts)
    display_username: Optional[str] = None    # Social username OR hiring company
    display_location: Optional[str] = None    # Location
    display_link: Optional[str] = None        # URL to original (job_posting_url or post_url)
    display_source: Optional[str] = None      # "LinkedIn Jobs" OR "X" OR "Reddit"

    # ========================================
    # USER ACTIONS (PRD Section 3.5, 3.6)
    # ========================================
    user_reviewed: bool = False                       # Has user viewed this spam item?
    promoted_to_leads: bool = False                   # PRD 3.5: "Add to Leads" action
    promoted_at: Optional[datetime] = None
    moved_from_leads: bool = False                    # PRD 3.6: Reverse action (Lead → Spam)
    moved_from_leads_at: Optional[datetime] = None
    user_notes: Optional[str] = None                  # User's review notes

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class SpamLeadCreate(SpamLeadBase):
    """
    Model for creating a new spam lead
    Used when saving filtered items to spam collection
    """
    spam_id: str = Field(default_factory=lambda: str(ObjectId()))


class SpamLead(SpamLeadBase):
    """
    Full spam lead model with MongoDB ID
    Returned from database queries
    """
    id: str = Field(default_factory=lambda: str(ObjectId()))

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}
