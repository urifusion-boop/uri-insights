from typing import List, Optional
from app.core.helpers.dict_helper import DictHelper
from app.domain.adapters.ReportGenAdapter import ReportGenAdapter
from app.domain.enums.reportgeneration_enum import FacebookAccountKeysEnum


class FacebookAdapter(ReportGenAdapter):
    def __init__(self, data: dict):
        self.data = data

    def to_report_gen_metadata(self):
        try:
            current_period_insights, previous_period_insights, account_info = (
                self.extract_insight_data(self.data)
            )
        except Exception:
            raise

        post_data = account_info.get("post_data")

        metadata = {
            "account_info": self.extract_account_info_facebook(account_info),
            "current_period_insights": self.facebook_data_to_insight(
                current_period_insights
            ),
            "previous_period_insights": self.facebook_data_to_insight(
                previous_period_insights
            ),
            "post_data": post_data,
        }
        return metadata

    def facebook_data_to_insight(self, raw_insights_data) -> dict:
        engagement_data = None
        impressions_data = None
        demographics_data = None
        followers_data = None
        viewers_data = None

        for data in raw_insights_data:
            if data.get("name") == "page_post_engagements":
                engagement_data = data.get("values")
            elif data.get("name") == "page_impressions":
                impressions_data = data.get("values")
            elif data.get("name") == "page_fans_country":
                demographics_data = data.get("values")
            elif data.get("name") == "page_daily_follows":
                followers_data = data.get("values")
            elif data.get("name") == "page_impressions_unique":
                viewers_data = data.get("values")

        print("\n\nDEMOGRAPHICS DATA: ", demographics_data)

        insights = self.create_meta_insights_dict(
            engagement_data=engagement_data,
            impressions_data=impressions_data,
            followers_data=followers_data,
            viewers_data=viewers_data,
        )

        if demographics_data:
            insights["audience_location"] = self.__extract_audience_demographics(
                demographics_data
            )

        return insights

    def extract_account_info_facebook(self, data: dict) -> dict:
        keys = [
            FacebookAccountKeysEnum.NAME.value,
            FacebookAccountKeysEnum.FOLLOWERS_COUNT.value,
            FacebookAccountKeysEnum.USERNAME.value,
        ]
        account_info = {key: data[key] for key in data if key in keys}
        return account_info

    def __extract_audience_demographics(self, data: List[dict]) -> Optional[dict]:
        data = [
            demographic_info.get("value", {})
            for demographic_info in data
            if demographic_info
        ]
        if not data:
            raise ValueError("Audience demographics failed to be generated")
        result = DictHelper.sum_dict_values(data)
        return result

    def extract_insight_data(self, data: dict):
        current_period_insights = data.get("current_period_insights", {}).get("data")
        previous_period_insights = data.get("previous_period_insights", {}).get("data")
        account_info = data.get("account_info")

        if (
            not current_period_insights
            or not previous_period_insights
            or not account_info
        ):
            raise ValueError("Incomplete data for generating report")

        return current_period_insights, previous_period_insights, account_info
