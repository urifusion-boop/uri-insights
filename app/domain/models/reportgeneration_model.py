from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ReportMetadataModel(BaseModel):
    account_info: dict
    current_period_insights: dict | list
    previous_period_insights: dict | list
    since: Optional[datetime] = None
    until: Optional[datetime] = None
    current_sentiment_analysis: Optional[dict] = None
    previous_sentiment_analysis: Optional[dict] = None
