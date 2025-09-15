"""This module serves as the base module for all analytics requests with common request structures
"""

from pydantic import BaseModel
from app.domain.enums.date_enum import DateFilterEnum


class AnalyticsRequest(BaseModel):
    """The base class for analytics requests"""

    user_id: str
    date_filter: DateFilterEnum = DateFilterEnum.LAST_7_DAYS
