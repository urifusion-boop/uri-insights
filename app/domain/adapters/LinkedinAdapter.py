from typing import List, Any, Dict
from app.core.helpers.date_helper import DateHelper
from app.domain.adapters.ReportGenAdapter import ReportGenAdapter


class LinkedinAdapter(ReportGenAdapter):
    def __init__(self, data: dict):
        self.data = data

    def to_report_gen_metadata(self):
        current_period_insights = self.data.get("current_period_insights")
        previous_period_insights = self.data.get("previous_period_insights")
        account_info = self.data.get("account_info")

        posts = account_info.get("posts")

        metadata = {
            "account_info": self.extract_account_info_linkedin(account_info),
            "current_period_insights": self.extract_insights_from_raw_data(
                current_period_insights
            ),
            "previous_period_insights": self.extract_insights_from_raw_data(
                previous_period_insights
            ),
            "post_data": posts,
        }

        return metadata

    def extract_account_info_linkedin(self, data: dict) -> dict:
        return {
            "name": data.get("localizedName"),
            "username": data.get("vanityName"),
            "followers_count": data.get("follower_count", {}).get("firstDegreeSize", 0),
            "following_count": data.get("", 0),
        }

    def extract_insights_from_raw_data(self, data: List[dict]):
        insights_dict: Dict[str, Any] = {
            "engagements": {},
            "impressions": {},
            "followers": {},
            "viewers": {},
        }
        for item in data:
            key = DateHelper.to_iso_format(item.get("timeRange", {}).get("end", 0))
            if not key:
                raise ValueError(
                    "Datetime key not generated to store insights data in insights dictionary"
                )
            if "totalShareStatistics" in item:
                item_statistics = item.get("totalShareStatistics", {})
                like_count = item_statistics.get("likeCount")
                click_count = item_statistics.get("clickCount")
                share_count = item_statistics.get("shareCount")
                impression_count = item_statistics.get("impressionCount")
                viewer_count = item_statistics.get("uniqueImpressionsCount")
                engagements = like_count + click_count + share_count
                insights_dict["engagements"][key] = engagements
                insights_dict["impressions"][key] = impression_count
                insights_dict["viewers"][key] = viewer_count
            elif "followerGains" in item:
                item_statistics = item.get("followerGains")
                insights_dict["followers"][key] = item_statistics.get(
                    "organicFollowerGain"
                )

        return insights_dict
