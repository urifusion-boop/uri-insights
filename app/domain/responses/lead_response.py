from pydantic import BaseModel
from typing import Dict, Optional


# Response model for aggregated analytics
class LeadAnalyticsResponse(BaseModel):
    new_leads: int
    contacted: int
    qualified: int
    unqualified: int
    converted: int
    lead_sources_breakdown: Dict[str, int]
    leads_by_industry: Dict[str, int]
    interest_by_platform: Dict[str, Dict[str, int]]


class ImportedConversationalLeadEnrichmentResponse(BaseModel):
    summary_of_mention: Optional[str] = None
    follow_up_message: Optional[str] = None  # Personalized follow-up message
    follow_up_approach: Optional[str] = (
        None  # Best approach for following up (e.g., Email, LinkedIn)
    )
