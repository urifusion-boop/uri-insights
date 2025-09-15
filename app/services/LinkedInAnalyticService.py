import requests
from typing import Dict
from app.domain.responses.uri_response import UriResponse
import urllib.parse


class LinkedInAnalyticService:

    @staticmethod
    async def fetch_analytics(
        bearer_token: str,
        pivot: str,
        campaign_id: str,
        time_granularity: str,
        start_date: Dict,  # Date range with 'year', 'month', 'day' keys
        end_date: Dict,
    ):
        base_url = "https://api.linkedin.com/rest/adAnalytics"

        campaign_urn = f"urn:li:sponsoredCampaign:{campaign_id}"
        encoded_campaign = f"List({urllib.parse.quote(campaign_urn)})"

        # Build the date range string (assuming dictionary with year, month, day keys)
        start_date_str = f"(year:{start_date['year']},month:{start_date['month']},day:{start_date['day']})"
        end_date_str = (
            f"(year:{end_date['year']},month:{end_date['month']},day:{end_date['day']})"
        )
        date_range = f"(start:{start_date_str},end:{end_date_str})"

        full_url = (
            f"{base_url}?q=analytics"
            f"&pivot={pivot}"
            f"&timeGranularity={time_granularity}"
            f"&dateRange={date_range}"
            f"&campaigns={encoded_campaign}"
        )

        print("full_url", full_url)

        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Linkedin-Version": "202405",
        }

        response = requests.get(full_url, headers=headers)

        return UriResponse.get_single_data_response(
            entity_name="analytics", data=response.json()
        )
