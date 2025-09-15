from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class AiRecommendationResponse(BaseModel):
    title: str
    text: str


class AlertAnalyticsResponse(BaseModel):
    high_priority_alerts: Optional[List[dict]]
    total_alerts: Optional[int]
    positive_alerts: Optional[int]
    negative_alerts: Optional[int]
    neutral_alerts: Optional[int]
    platform_breakdown: Optional[Dict[str, Any]]
    ai_recommendation: Optional[AiRecommendationResponse]
    analytics_over_time: Optional[Dict[Any, Any]]
