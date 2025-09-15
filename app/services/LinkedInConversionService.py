import requests
import json
from app.domain.requests.linkedin_requests import *
from app.domain.responses.uri_response import UriResponse


class LinkedInConversionService:

    @staticmethod
    async def create_conversion_rule(request: CreateConversionRuleRequest):
        url = f"https://api.linkedin.com/rest/conversions"

        body = request.model_dump(
            by_alias=True,
            exclude_unset=True,
            exclude_none=True,
            exclude={"bearer_token": True, "account_id": True},
        )
        body["account"] = f"urn:li:sponsoredAccount:{request.account_id}"

        headers = {
            "Authorization": f"Bearer {request.bearer_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
            "Linkedin-Version": "202401",
        }

        response = requests.post(url, data=json.dumps(body), headers=headers)

        return UriResponse.create_response(entity_name="conversion rule", data=True)

    @staticmethod
    async def fetch_conversion_rules(ad_account_id: str, bearer_token: str):
        base_url = f"https://api.linkedin.com/rest/conversions"

        full_url = f"{base_url}?q=account&account=urn%3Ali%3AsponsoredAccount%3A{ad_account_id}"

        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Linkedin-Version": "202401",
        }

        response = requests.get(full_url, headers=headers)

        return UriResponse.get_single_data_response(
            entity_name="conversion rule", data=response.json()
        )

    @staticmethod
    async def associate_conversion_rule_to_campaign(
        request: LinkConversionToCampaignRequest,
    ):
        base_url = f"https://api.linkedin.com/rest/campaignConversions"

        full_url = f"{base_url}/(campaign:urn%3Ali%3AsponsoredCampaign%{request.campaign_id},conversion:urn%3Alla%3AllaPartnerConversion%{request.conversion_id})"

        body = {
            "campaign": f"urn:li:sponsoredCampaign:{request.campaign_id}",
            "conversion": f"urn:lla:llaPartnerConversion:{request.conversion_id}",
        }

        headers = {
            "Authorization": f"Bearer {request.bearer_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
            "Linkedin-Version": "202401",
        }

        response = requests.put(full_url, data=json.dumps(body), headers=headers)

        return UriResponse.update_response(entity_name="campaign", data=response.json())

    @staticmethod
    async def stream_conversion_events(request: StreamConversionEventRequest):
        url = f"https://api.linkedin.com/rest/conversionEvents"

        body = {
            "conversion": f"urn:lla:llaPartnerConversion:{request.conversion_id}",
            "conversionHappenedAt": request.conversion_happened_at,
            "conversionValue": request.conversion_value,
            "user": request.user,
            "eventId": request.event_id,
        }

        headers = {
            "Authorization": f"Bearer {request.bearer_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
            "Linkedin-Version": "202401",
        }

        response = requests.post(url, data=json.dumps(body), headers=headers)

        return UriResponse.create_response(
            entity_name="conversion event", data=response.json()
        )
