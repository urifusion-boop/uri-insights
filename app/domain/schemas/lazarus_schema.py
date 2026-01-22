"""
Lazarus Protocol Schemas

Separate schema file for the Lazarus resurrection system.
Does NOT extend or modify existing lead form schemas.

The Lazarus Protocol monitors "dead leads" for signals that they're ready to buy:
- Focus Contacts (Individuals): Track job changes, complaints, buying intent
- Company Monitors: Track hiring, funding, pivots, website changes
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from bson import ObjectId
from enum import Enum


# ========================================
# ENUMS
# ========================================

class LazarusMonitorTypeEnum(str, Enum):
    """Type of entity being monitored"""
    FOCUS_CONTACT = "FOCUS_CONTACT"  # Individual person
    COMPANY = "COMPANY"  # Company/organization


class LazarusMonitoringStatusEnum(str, Enum):
    """Monitoring status"""
    ACTIVE = "ACTIVE"  # Currently being monitored
    PAUSED = "PAUSED"  # User paused monitoring
    MOVED = "MOVED"  # Contact changed jobs (detected)
    DEAD = "DEAD"  # Company/contact is verified dead
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"  # User hit slot limit


class LazarusAlertTypeEnum(str, Enum):
    """Types of resurrection signals (PRD Section 3)"""
    # Focus Contact Alerts
    JOB_EXIT = "JOB_EXIT"  # Removed company from bio
    CHAMPION_MOVE = "CHAMPION_MOVE"  # Moved to new company
    PAIN_SIGNAL = "PAIN_SIGNAL"  # Complaining about competitor
    BUYING_INTENT = "BUYING_INTENT"  # Asking for recommendations

    # Company Alerts
    HIRING_SPREE = "HIRING_SPREE"  # Added multiple job postings
    CASH_INJECTION = "CASH_INJECTION"  # Received funding
    STRATEGIC_PIVOT = "STRATEGIC_PIVOT"  # Changed product/service offering
    COMPANY_DEAD = "COMPANY_DEAD"  # Website offline (obituary)


class LazarusAlertStatusEnum(str, Enum):
    """Alert status for user actions"""
    NEW = "NEW"  # Just detected
    VIEWED = "VIEWED"  # User opened the alert
    ACTED = "ACTED"  # User took action (pitched)
    DISMISSED = "DISMISSED"  # User marked as not helpful


class LazarusPlanTypeEnum(str, Enum):
    """Subscription plan types (PRD Section 2.1)"""
    BASIC = "BASIC"  # 50 active slots
    PRO = "PRO"  # 500 active slots


# ========================================
# FOCUS CONTACT (Individual Monitoring)
# ========================================

class FocusContact(BaseModel):
    """
    PRD Section 4.1 - Focus Contact tracking

    Monitors individuals for:
    - Job changes (bio diffing)
    - Pain signals (complaints on social media)
    - Buying intent (asking for recommendations)
    """
    focus_id: str = Field(default_factory=lambda: str(ObjectId()))
    user_id: str

    # Identity
    name: str
    social_handle: Optional[str] = None  # twitter.com/username, linkedin.com/in/username
    linkedin_url: Optional[str] = None
    twitter_url: Optional[str] = None
    current_company: Optional[str] = None

    # Bio tracking for job changes
    last_bio_text: Optional[str] = None
    last_bio_hash: Optional[str] = None  # MD5 hash for comparison
    bio_last_checked: Optional[datetime] = None

    # Industry keywords for tweet monitoring
    industry_keywords: List[str] = []  # ["logistics", "inverter", "diesel"]

    # Monitoring state
    monitoring_status: LazarusMonitoringStatusEnum = LazarusMonitoringStatusEnum.ACTIVE
    last_scan_date: Optional[datetime] = None
    next_scan_date: Optional[datetime] = None
    scan_frequency_days: int = 7  # How often to scan (default: weekly)
    scan_count: int = 0  # Number of scans performed
    alert_count: int = 0  # Number of alerts generated

    # Link to original lead (if came from existing system)
    source_lead_id: Optional[str] = None  # Link to leads collection

    # Why was this marked as dead?
    marked_dead_reason: Optional[str] = None  # "Closed-Lost", "Ghosted", "No Budget"
    marked_dead_date: Optional[datetime] = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    slot_count: int = 1  # Each contact = 1 slot

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


# ========================================
# COMPANY MONITOR
# ========================================

class CompanyMonitor(BaseModel):
    """
    PRD Section 3 Track A - Company monitoring

    Monitors companies for:
    - Hiring sprees (job board scraping)
    - Cash injections (Google News)
    - Strategic pivots (homepage changes)
    - Company death (404 errors)
    """
    monitor_id: str = Field(default_factory=lambda: str(ObjectId()))
    user_id: str

    # Identity
    company_name: str
    website_url: Optional[str] = None
    domain: Optional[str] = None  # Extracted from website_url
    location: Optional[str] = None  # e.g., "Lagos, Nigeria" or "Remote"
    country_code: Optional[str] = None  # e.g., "ng", "us", "uk" - for Google Search

    # Homepage tracking for pivots
    last_homepage_hash: Optional[str] = None  # MD5 hash
    last_homepage_text: Optional[str] = None  # For keyword detection
    homepage_last_checked: Optional[datetime] = None

    # Job board tracking for hiring sprees
    last_job_count: int = 0
    jobs_last_checked: Optional[datetime] = None

    # News tracking for funding
    last_news_check: Optional[datetime] = None

    # 404 tracking for company death
    consecutive_404_count: int = 0  # PRD: Flag as dead after 4 weeks (4 checks)
    first_404_date: Optional[datetime] = None

    # Industry keywords for news search
    industry_keywords: List[str] = []

    # Monitoring state
    monitoring_status: LazarusMonitoringStatusEnum = LazarusMonitoringStatusEnum.ACTIVE
    last_scan_date: Optional[datetime] = None
    next_scan_date: Optional[datetime] = None
    scan_frequency_days: int = 7  # How often to scan (default: weekly)
    scan_count: int = 0  # Number of scans performed
    alert_count: int = 0  # Number of alerts generated

    # Link to original lead
    source_lead_id: Optional[str] = None

    # Why was this marked as dead?
    marked_dead_reason: Optional[str] = None
    marked_dead_date: Optional[datetime] = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    slot_count: int = 1

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


# ========================================
# LAZARUS ALERTS (Resurrection Signals)
# ========================================

class LazarusAlertEvidence(BaseModel):
    """Evidence for the resurrection signal"""
    # For job changes
    old_bio: Optional[str] = None
    new_bio: Optional[str] = None
    old_company: Optional[str] = None
    new_company: Optional[str] = None

    # For social signals (platform-agnostic)
    post_url: Optional[str] = None  # URL to the post (LinkedIn, Twitter, TikTok, Facebook)
    post_text: Optional[str] = None  # Content of the post
    post_platform: Optional[str] = None  # "LinkedIn", "Twitter", "TikTok", "Facebook"

    # Legacy fields (backward compatibility)
    tweet_url: Optional[str] = None
    tweet_text: Optional[str] = None

    # For company signals
    news_url: Optional[str] = None
    news_title: Optional[str] = None
    old_job_count: Optional[int] = None
    new_job_count: Optional[int] = None

    # For homepage changes
    detected_keywords: Optional[List[str]] = None

    # AI Analysis fields (for buying signal detection)
    signal_type: Optional[str] = None  # "pain", "switch", "hiring", "funding"
    confidence: Optional[float] = None  # 0.0 to 1.0
    evidence_text: Optional[str] = None  # AI-extracted evidence text
    signal_source: Optional[str] = None  # "LinkedIn (AI Analysis)", "Twitter + LinkedIn (AI Analysis)", etc.


class LazarusAlert(BaseModel):
    """
    PRD Section 5.2 - Resurrection Card

    Alert generated when a signal is detected
    """
    alert_id: str = Field(default_factory=lambda: str(ObjectId()))
    user_id: str

    # Source of alert
    source_type: LazarusMonitorTypeEnum
    source_id: str  # focus_id or monitor_id
    source_name: str  # Contact name or company name

    # Alert details
    alert_type: LazarusAlertTypeEnum
    alert_message: str  # PRD Section 3: "Expansion Detected: Added 3 new roles"
    evidence: LazarusAlertEvidence

    # AI-generated pitch (PRD Section 5.2.4)
    suggested_pitch: Optional[str] = None

    # User actions
    status: LazarusAlertStatusEnum = LazarusAlertStatusEnum.NEW
    viewed_at: Optional[datetime] = None
    acted_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None
    user_feedback: Optional[str] = None  # "Not Helpful", "Great Lead", etc.

    # Link to original lead
    source_lead_id: Optional[str] = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


# ========================================
# QUOTA MANAGEMENT (PRD Section 2.1)
# ========================================

class LazarusSlots(BaseModel):
    """
    PRD Section 2.1 - The Quota System

    Manages user's monitoring slot allocation
    """
    user_id: str

    # Plan limits
    plan_type: LazarusPlanTypeEnum = LazarusPlanTypeEnum.BASIC
    max_slots: int = 50  # Basic: 50, Pro: 500

    # Current usage
    used_slots: int = 0
    focus_contacts_count: int = 0
    company_monitors_count: int = 0

    # Tracking
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


# ========================================
# REQUEST/RESPONSE MODELS
# ========================================

class FocusContactCreate(BaseModel):
    """Create a new focus contact monitor"""
    name: str
    social_handle: Optional[str] = None
    last_bio_text: Optional[str] = None
    linkedin_url: Optional[str] = None
    twitter_url: Optional[str] = None
    current_company: Optional[str] = None
    industry_keywords: List[str] = []
    scan_frequency_days: Optional[int] = 7  # Default: weekly scans
    marked_dead_reason: Optional[str] = None
    source_lead_id: Optional[str] = None


class CompanyMonitorCreate(BaseModel):
    """Create a new company monitor"""
    company_name: str
    website_url: Optional[str] = None
    location: Optional[str] = None  # e.g., "Lagos, Nigeria" or "Remote"
    country_code: Optional[str] = None  # e.g., "ng", "us", "uk"
    last_homepage_content: Optional[str] = None
    last_job_count: int = 0
    industry_keywords: List[str] = []
    scan_frequency_days: Optional[int] = 7  # Default: weekly scans
    marked_dead_reason: Optional[str] = None
    source_lead_id: Optional[str] = None


class CSVUploadRow(BaseModel):
    """Single row from CSV upload (PRD Section 2.2.1)"""
    type: LazarusMonitorTypeEnum
    name: str
    social_handle: Optional[str] = None
    current_bio: Optional[str] = None
    website_url: Optional[str] = None
    location: Optional[str] = None  # For companies
    country_code: Optional[str] = None  # For companies
    industry_keywords: Optional[List[str]] = None
    scan_frequency_days: Optional[int] = 7  # Default: weekly scans


class LazarusMetrics(BaseModel):
    """
    PRD Section 7 - Success Metrics

    Dashboard metrics for user
    """
    # Quota
    used_slots: int
    max_slots: int
    utilization_percent: float

    # Monitoring
    active_focus_contacts: int
    active_company_monitors: int

    # Resurrections
    total_alerts: int
    new_alerts: int
    resurrected_leads: int

    # Engagement (PRD 7.1)
    resurrection_rate: float  # % of alerts acted upon

    # Recommendations
    should_upgrade: bool  # If near quota limit
    upgrade_from: str
    upgrade_to: str


# ========================================
# AUTO-DETECTION RULES & HISTORY
# ========================================

class DetectionRules(BaseModel):
    """Rules for auto-detecting dead leads and monitoring buying signals"""
    no_response_days: int = 30  # Mark dead if no activity in X days
    status_unchanged_days: Optional[int] = 60  # Mark dead if status unchanged
    min_contact_attempts: int = 2  # Minimum contact attempts required
    exclude_statuses: List[str] = ["Qualified", "Converted"]  # Never auto-mark these
    auto_add_to_lazarus: bool = False  # Auto-add to Lazarus monitoring
    monitor_type: str = "focus_contact"  # "focus_contact" or "company_monitor"
    signal_types: List[str] = ["funding", "hiring", "pain", "switch"]  # Buying signals to monitor

    class Config:
        extra = "forbid"


class AutoDetectionSettings(BaseModel):
    """User's auto-detection settings"""
    user_id: str
    enabled: bool = False
    detection_rules: DetectionRules
    schedule: str = "weekly"  # "daily", "weekly", "monthly"
    last_scan_date: Optional[datetime] = None
    next_scan_date: Optional[datetime] = None
    created_date: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class DetectionRulesUpdate(BaseModel):
    """Schema for updating detection rules"""
    enabled: Optional[bool] = None
    detection_rules: Optional[DetectionRules] = None
    schedule: Optional[str] = None

    class Config:
        extra = "forbid"


class ScanHistoryRecord(BaseModel):
    """Record of an auto-detection scan"""
    user_id: str
    scan_date: datetime
    scanned_leads: int
    marked_dead: int
    added_to_lazarus: int
    errors: List[Dict[str, Any]] = []

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class ScanResponse(BaseModel):
    """Response from manual or automated scan"""
    scanned_leads: int
    marked_dead: int
    added_to_lazarus: int
    errors: List[Dict[str, Any]] = []
    timestamp: datetime

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


# ========================================
# AI RESPONSE MODELS
# ========================================

class BuyingSignalAnalysis(BaseModel):
    """AI analysis result for buying signal detection"""
    signal_detected: bool
    signal_type: Optional[str] = None  # "pain", "switch", "hiring", "funding"
    confidence: float
    evidence: Optional[str] = None
    reason: Optional[str] = None


class KeywordExtractionResult(BaseModel):
    """AI result for keyword extraction from posts"""
    keywords: List[str]
    confidence: float
    reasoning: Optional[str] = None


class KeywordExtractionRequest(BaseModel):
    """Request schema for keyword extraction"""
    name: Optional[str] = None
    bio: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    recent_post: Optional[str] = None
    signal_types: List[str] = ["pain", "switch", "hiring", "funding"]
