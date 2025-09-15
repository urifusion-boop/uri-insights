import requests
import json
from app.domain.requests.linkedin_requests import *
from app.domain.responses.uri_response import UriResponse


class LinkedInCampaignService:

    @staticmethod
    def create_campaign_group(request: CreateCampaignGroupRequest):
        url = f"https://api.linkedin.com/rest/adAccounts/{request.account}/adCampaignGroups"

        body = request.model_dump(
            by_alias=True,
            exclude_unset=True,
            exclude_none=True,
            exclude={"bearer_token": True},
        )
        body["account"] = f"urn:li:sponsoredAccount:{request.account}"

        headers = {
            "Authorization": f"Bearer {request.bearer_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
            "Linkedin-Version": "202401",
        }

        requests.post(url, data=json.dumps(body), headers=headers)

        return UriResponse.create_response(entity_name="campaign group", data=True)

    @staticmethod
    def fetch_campaign_group(
        account_id: str, campaign_group_id: str, bearer_token: str
    ):
        url = f"https://api.linkedin.com/rest/adAccounts/{account_id}/adCampaignGroups/{campaign_group_id}"

        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Linkedin-Version": "202401",
        }

        response = requests.get(url, headers=headers)

        return UriResponse.get_single_data_response(
            entity_name="campaign group", data=response.json()
        )

    @staticmethod
    def search_campaign_groups(
        account_id: str, status: str, sort_order: str, bearer_token: str
    ):
        base_url = (
            f"https://api.linkedin.com/rest/adAccounts/{account_id}/adCampaignGroups"
        )

        full_url = f"{base_url}?q=search&search=(status:(values:List({status})))&sortOrder={sort_order}"

        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Linkedin-Version": "202401",
        }

        response = requests.get(full_url, headers=headers)

        return UriResponse.get_list_data_response(
            entity_name="campaign group", data=response.json()
        )

    @staticmethod
    def update_campaign_group(request: UpdateCampaignGroupRequest):
        url = f"https://api.linkedin.com/rest/adAccounts/{request.ad_account_id}/adCampaignGroups/{request.campaign_group_id}"

        body = {"patch": {"$set": request.set}}

        headers = {
            "Authorization": f"Bearer {request.bearer_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
            "Linkedin-Version": "202401",
        }

        response = requests.post(url, data=body, headers=headers)

        return UriResponse.update_response(
            entity_name="campaign group", data=response.json()
        )

    @staticmethod
    def create_campaign(request: CreateCampaignRequest):
        url = f"https://api.linkedin.com/rest/adAccounts/{request.ad_account_id}/adCampaigns"

        body = request.model_dump(
            by_alias=True,
            exclude_unset=True,
            exclude_none=True,
            exclude={
                "ad_account_id": True,
                "campaign_group_id": True,
                "bearer_token": True,
            },
        )
        body["account"] = f"urn:li:sponsoredAccount:{request.ad_account_id}"
        body["campaignGroup"] = (
            f"urn:li:sponsoredCampaignGroup:{request.campaign_group_id}"
        )

        headers = {
            "Authorization": f"Bearer {request.bearer_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
            "Linkedin-Version": "202401",
        }

        requests.post(url, data=json.dumps(body), headers=headers)

        return UriResponse.create_response(entity_name="campaign", data=True)

    @staticmethod
    def fetch_campaign(account_id: str, campaign_id: str, bearer_token: str):
        url = f"https://api.linkedin.com/rest/adAccounts/{account_id}/adCampaigns/{campaign_id}"

        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Linkedin-Version": "202401",
        }

        response = requests.get(url, headers=headers)

        return UriResponse.get_single_data_response(
            entity_name="campaign group", data=response.json()
        )

    @staticmethod
    def search_campaigns(
        account_id: str,
        campaign_type: str,
        status: str,
        sort_order: str,
        bearer_token: str,
    ):
        base_url = f"https://api.linkedin.com/rest/adAccounts/{account_id}/adCampaigns"

        full_url = f"{base_url}?q=search&search=(type:(values:List({campaign_type})),status:(values:List({status})))&sortOrder={sort_order}"

        print(full_url)

        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Linkedin-Version": "202401",
        }

        response = requests.get(full_url, headers=headers)

        return UriResponse.get_list_data_response(
            entity_name="campaign group", data=response.json()
        )

    @staticmethod
    def update_campaign(request: UpdateCampaignRequest):
        url = f"https://api.linkedin.com/rest/adAccounts/{request.ad_account_id}/adCampaigns/{request.campaign_id}"

        body = {"patch": {"$set": request.set}}

        headers = {
            "Authorization": f"Bearer {request.bearer_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
            "Linkedin-Version": "202401",
        }

        response = requests.post(url, data=body, headers=headers)

        return UriResponse.update_response(
            entity_name="campaign group", data=response.json()
        )
