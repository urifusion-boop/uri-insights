from collections import defaultdict
from datetime import datetime
from typing import Any, List, Optional
from app.core.helpers.date_helper import DateHelper
from app.core.helpers.dict_helper import DictHelper
from app.domain.adapters.BaseAdapter import BaseAdapter
from app.domain.enums.reportgeneration_enum import FacebookAccountKeysEnum


class ReportGenAdapter(BaseAdapter):
    def __init__(self, data: dict):
        self.data = data

    def create_meta_insights_dict(
        self,
        engagement_data=None,
        impressions_data=None,
        followers_data=None,
        viewers_data=None,
    ):
        insights = {
            "engagements": (
                self.__extract_meta_insights_data(engagement_data)
                if engagement_data
                else None
            ),
            "impressions": (
                self.__extract_meta_insights_data(impressions_data)
                if impressions_data
                else None
            ),
            "followers": (
                self.__extract_meta_insights_data(followers_data)
                if followers_data
                else None
            ),
            "viewers": (
                self.__extract_meta_insights_data(viewers_data)
                if viewers_data
                else None
            ),
        }

        return insights

    def __extract_meta_insights_data(self, data: List[dict]) -> dict:
        print("Data: ", data)
        result = {}
        for item in data:
            key = item.get("end_time")
            value = item.get("value")
            if key:
                parsed_date = DateHelper.format_to_iso8601(key)
                result[parsed_date] = value or 0
        return result
