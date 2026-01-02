"""
Spam Enums - Classification reasons for unqualified leads

PRD Reference: Lead Gen Enhancement PRD - Section 3.4
Each spam item must display reason(s) for disqualification
"""

from enum import Enum


class SpamReasonEnum(str, Enum):
    """
    Why a lead was marked as spam (analyzed but unqualified)

    PRD Section 3.4 - Required reasons:
    - Low problem–solution match
    - Missing company
    - Low intent signal
    - Budget confidence too low
    """

    # ========================================
    # JOB BOARD REASONS (Sales Signals)
    # PRD Section 3.4
    # ========================================
    LOW_PROBLEM_SOLUTION_MATCH = "Low problem–solution match"
    LOW_COMMERCIAL_RELEVANCE = "Low commercial relevance"
    LOW_HIRING_INTENT = "Low hiring intent signal"
    MISSING_COMPANY = "Missing company information"
    LOW_COMPANY_CONFIDENCE = "Company confidence too low"

    # ========================================
    # SOCIAL POST REASONS (Intent Analysis)
    # Not explicitly in PRD but needed for social posts
    # ========================================
    LOW_INTENT_SCORE = "Low buying intent"
    LOW_RELEVANCE_SCORE = "Low relevance to business"
    FAILED_INTENT_ANALYSIS = "Failed intent qualification"
    LOW_FINAL_SCORE = "Low combined qualification score"

    # ========================================
    # OTHER FILTER REASONS
    # ========================================
    OUTSIDE_TIME_WINDOW = "Post outside target time range"
    LOCATION_MISMATCH = "Location does not match target"
    DUPLICATE_CONTENT = "Duplicate post detected"
    ANALYSIS_ERROR = "Analysis error occurred"


class SpamFilterStageEnum(str, Enum):
    """
    Which filter stage marked this item as spam
    Used for filtering and analytics
    """
    JOB_BOARD_AI = "job_board_ai"           # Failed commercial_relevance < 0.3
    INTENT_ANALYSIS = "intent_analysis"     # Failed intent/relevance/final scores
    TIME_FILTER = "time_filter"             # Outside time window
    LOCATION_FILTER = "location_filter"     # Location mismatch
    DUPLICATE = "duplicate"                 # Duplicate content detected
