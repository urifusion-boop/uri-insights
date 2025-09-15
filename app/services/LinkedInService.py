from datetime import datetime
from fastapi import HTTPException
import requests
from http import HTTPStatus
from typing import Any, Dict, List, Optional
from http import HTTPStatus
import requests
from app.core.config import settings
from app.core.helpers.linkedin_helper import LinkedinHelper
from app.core.helpers.reportgeneration_helper import ReportGenerationHelper
from app.domain.enums.account_enum import AccountTypeEnum
from app.domain.enums.endpoints_enum import EndpointsEnum
from app.domain.enums.linkedin_enum import (
    LinkedInTimeGranularityEnum,
    LinkedInTokenScopeEnum,
    LinkedinUrnNamespaceEnum,
)
from app.domain.enums.socialmediapost_enum import PostPlatformEnum
from app.domain.models.reportgeneration_model import ReportMetadataModel
from app.domain.requests.reportgeneration_requests import ReportGenerationRequest
from app.domain.responses.uri_response import UriResponse
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from pymongo.collection import Collection
from app.repository.InfluencerRepository import InfluencerRepository
from app.domain.schemas import influencer_schema
from app.services.EmbeddingService import EmbeddingService
from app.services.FeatureLimitService import FeatureLimitService
from app.services.LinkedInCommunityMgtService import LinkedInCommunityMgtService


class LinkedInService:
    BASE_URL = "https://api.linkedin.com/v2"

    @staticmethod
    async def fetch_discovery(
        access_token: str,
        fields: Optional[
            str
        ] = None,  # Optional fields, but LinkedIn userinfo has a predefined set
    ):
        base_url = f"{LinkedInService.BASE_URL}/me"  # Updated endpoint for LinkedIn user profile
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        if fields:
            print(
                "Note: The LinkedIn /me API does not support custom fields. Ignoring 'fields'."
            )

        try:
            response = requests.get(url=base_url, headers=headers)

            if response.status_code != HTTPStatus.OK:
                return {
                    "status": "error",
                    "message": f"Failed to fetch user data from LinkedIn. Status code: {response.status_code}",
                    "details": response.text,
                }

            result = response.json()
            return UriResponse.get_single_data_response("Linkedin discovery", result)

        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "message": "An error occurred while connecting to LinkedIn API.",
                "details": str(e),
            }

    @staticmethod
    async def save_linkedin_account(
        user_id: str,
        access_token: str,
        token_scope: LinkedInTokenScopeEnum,
        db: AsyncIOMotorDatabase,
        max_accounts: int,
    ):
        # Fetch LinkedIn account details
        max_accounts = max_accounts
        discovery = await LinkedInService.fetch_discovery(access_token)
        user_pages_response = await LinkedInService.get_linkedin_user_pages(
            access_token
        )
        user_pages = user_pages_response.get("responseData", None)

        if discovery and discovery.get("status") == True:

            linkedin_user = discovery.get("responseData", None)

            if linkedin_user:
                # Create influencers for user
                influencers: List[influencer_schema.InfluencerCreate] = []

                if user_pages_response.get("status") and user_pages:
                    count = 0
                    amount_of_pages = len(user_pages)
                    while count < max_accounts and count < amount_of_pages:
                        influencers.append(
                            LinkedinHelper.construct_organization_influencer_creation_data(
                                user_id, user_pages[count], access_token, token_scope
                            )
                        )
                        count += 1
                # Create influencers for user account and linked pages if linked pages exist
                if influencers:
                    for influencer in influencers:
                        if influencer.profile_pic:
                            if influencer.account_type == AccountTypeEnum.PERSONAL:
                                influencer.profile_pic = (
                                    await LinkedInService.__get_user_profile_pic(
                                        access_token
                                    )
                                )
                            elif (
                                influencer.account_type == AccountTypeEnum.PROFESSIONAL
                            ):
                                influencer.profile_pic = await LinkedInService.__get_organization_profile_pic(
                                    access_token, influencer.social_user_id
                                )

                        # Perform a create or update operation
                        save_result = (
                            await InfluencerRepository.create_or_update_influencer(
                                db, influencer
                            )
                        )
                        if not save_result.get("success"):
                            print(
                                f"Error saving influencer: {influencer.social_username}"
                            )

                influencer_data = await InfluencerRepository.get_influencers_by_filter(
                    db, user_id
                )

                await FeatureLimitService.sync_specific_feature_limit_for_user(
                    db,
                    user_id,
                    EndpointsEnum.SAVE_LINKEDIN_ACCOUNTS.value,
                    PostPlatformEnum.LINKEDIN.value,
                )

                return UriResponse.get_single_data_response(
                    "influencer accounts", influencer_data
                )

            return UriResponse.get_single_data_response("Linkedin account", None)

        return UriResponse.get_single_data_response("Linkedin account", None)

    @staticmethod
    async def get_linkedin_urn(
        db: Collection, influencer_id: str, category: LinkedinUrnNamespaceEnum
    ) -> Dict:
        """
        Gets the sub of the linkedin user
        :influencer_id: Influencer's ID
        :Returns: Influencer sub
        """
        influencer = (
            await InfluencerRepository.get_influencer_by_id(db, influencer_id)
        ).get("responseData", None)
        if influencer:
            sub = influencer.get("social_user_id")
            user_urn = f"urn:li:{category.value.lower()}:{sub}"
            return UriResponse.get_single_data_response("linkedin urn", user_urn)
        return UriResponse.get_single_data_response("linkedin urn", None)

    @staticmethod
    async def get_linkedin_user_pages(access_token: str) -> Dict:
        """
        Retrieves LinkedIn pages associated with a user's LinkedIn account.

        Args:
            access_token (str): The OAuth2 access token for the LinkedIn API.

        Returns:
            Dict: Uri response containing list of dictionaries containing LinkedIn page details.
        """
        url = settings.LINKEDIN_PAGES_DISCOVERY_URL
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
        }
        params = {"q": "roleAssignee"}

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        # Extracting organization (page) details
        pages = []
        for element in data.get("elements", []):
            if "organization" in element:
                page_data = await LinkedInService.__get_linkedin_page_details(
                    access_token=access_token,
                    organization_urn_or_id=element["organization"],
                )
                pages.append(LinkedinHelper.extract_relevant_page_data(page_data))

        return UriResponse.get_list_data_response("linkedin user page", pages)

    @staticmethod
    async def __get_linkedin_page_details(
        access_token: str, organization_urn_or_id: str
    ) -> Dict[str, Any]:
        """
        Retrieves the details of a LinkedIn page using its organization URN or ID.

        Args:
            access_token (str): The OAuth2 access token for the LinkedIn API.
            organization_urn_or_id (str): The organization's URN (e.g., 'urn:li:organization:123456')
                                        or the numeric organization ID (e.g., '123456').

        Returns:
            Dict[str, Any]: A dictionary containing the LinkedIn page details.
        """
        # Extract the numeric ID if a URN is provided
        if organization_urn_or_id.startswith("urn:li:organization:"):
            organization_id = organization_urn_or_id.split(":")[-1]
        else:
            organization_id = organization_urn_or_id

        url = f"{LinkedInService.BASE_URL}/organizations/{organization_id}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    @staticmethod
    async def __get_user_profile_pic(
        access_token: str,
    ) -> Optional[str]:
        url = f"{LinkedInService.BASE_URL}/me?projection=(id,profilePicture(displayImage~digitalmediaAsset:playableStreams))"

        print("User profile Picture URL: ", url)

        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
        }

        response = requests.get(url=url, headers=headers)

        # Check response
        if response.status_code == 200:
            data = response.json()
            # Extract profile picture URL
            try:
                profile_picture = data["profilePicture"]["displayImage~"]["elements"][
                    -1
                ]["identifiers"][0]["identifier"]
                print("User profile Picture URL:", profile_picture)
                return profile_picture
            except KeyError:
                print("User profile picture not found.")
                return None
        else:
            print("Error:", response.json())
            return None

    @staticmethod
    async def __get_organization_profile_pic(
        access_token: str,
        organization_id: Optional[str],
    ) -> Optional[str]:
        url = f"{LinkedInService.BASE_URL}/organizations/{organization_id}?projection=(id,logoV2(original~:playableStreams))"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
        }

        response = requests.get(url=url, headers=headers)
        print("\nResponse: ", response.json())
        # Check response
        if response.status_code == 200:
            data = response.json()
            # Extract profile picture URL
            try:
                profile_picture = data["logoV2"]["original~"]["elements"][2][
                    "identifiers"
                ][0]["identifier"]
                print("Organization profile Picture URL:", profile_picture)
                return profile_picture
            except KeyError:
                print("Organization profile picture not found.")
                return None
        else:
            print("Error:", response)
            return None

    @staticmethod
    async def generate_raw_metadata_for_report_gen(
        db: AsyncIOMotorDatabase, report_generation_data: ReportGenerationRequest
    ):
        if (
            not report_generation_data.influencer_ids
            or not report_generation_data.influencer_ids.linkedin
        ):
            raise ValueError(
                "Influencer ID not provided for linkedin account tracking report gen"
            )
        token, social_id, _ = await ReportGenerationHelper.get_influencer_data(
            db,
            report_generation_data.influencer_ids.linkedin,
            report_generation_data.user_id,
        )
        token = token.get("ACCOUNT_TRACKING") or token.get("CONTENT_MANAGEMENT")
        if not token:
            raise ValueError(
                "Unauthorized request detected, try reconnecting your account."
            )
        start_date, end_date, previous_start = (
            ReportGenerationHelper.calculate_date_range(report_generation_data.period)
        )

        try:
            print("Getting period insights")
            current_period_insights = (
                await LinkedInService.generate_insights_for_report_gen(
                    db, token, social_id, start_date, end_date
                )
            )
            previous_period_insights = (
                await LinkedInService.generate_insights_for_report_gen(
                    db, token, social_id, previous_start, start_date
                )
            )
            business_discovery = (
                await LinkedInCommunityMgtService.fetch_business_discovery(
                    db=db,
                    organization_id=social_id,
                    access_token=token,
                )
            )
            metadata = ReportMetadataModel(
                account_info=business_discovery.get("responseData"),
                current_period_insights=current_period_insights,
                previous_period_insights=previous_period_insights,
                since=start_date,
                until=end_date,
            ).dict(exclude_none=True)
            return metadata
        except:
            raise

    @staticmethod
    async def generate_insights_for_report_gen(
        db: AsyncIOMotorDatabase,
        token: str,
        organization_id: str,
        start_time: datetime,
        end_time: datetime,
    ):
        share_statictics = (
            await LinkedInCommunityMgtService.retrieve_time_bound_share_statistics(
                db=db,
                organization_id=organization_id,
                access_token=token,
                start_time=start_time,
                end_time=end_time,
                time_granularity=LinkedInTimeGranularityEnum.DAY.value,
            )
        )
        follower_statistics = (
            await LinkedInCommunityMgtService.retrieve_time_bound_follower_statistics(
                db=db,
                organization_id=organization_id,
                access_token=token,
                start_time=start_time,
                end_time=end_time,
                time_granularity=LinkedInTimeGranularityEnum.DAY.value,
            )
        )

        aggregated_insights_statistics = share_statictics.get("responseData", {}).get(
            "elements"
        )
        aggregated_insights_statistics.extend(
            follower_statistics.get("responseData", {}).get("elements")
        )
        return aggregated_insights_statistics

    @staticmethod
    async def fetch_cached_linkedin_posts(
        db: AsyncIOMotorDatabase, linkedin_username: str, user_message: str
    ) -> dict:
        """
        Fetches cached LinkedIn posts for a given username.

        Args:
            db (AsyncIOMotorDatabase): The MongoDB database instance.
            linkedin_username (str): The LinkedIn username to fetch posts for.

        Returns:
            dict: A dictionary containing the fetched LinkedIn posts.
        """
        influencer = await InfluencerRepository.get_influencer_by_username(
            db, linkedin_username
        )

        # ✅ Ensure influencer exists before accessing properties
        if not influencer:
            return UriResponse.get_single_data_response(
                "linkedin posts for ai report",
                None,
                code=400,
                message="Influencer not found",
            )

        page_id = influencer.get("social_user_id", "")

        posts = await EmbeddingService.vector_search_account_tracking_data(
            db, page_id, PostPlatformEnum.LINKEDIN.value, user_message
        )

        return UriResponse.get_single_data_response(
            "linkedin posts for ai report", posts
        )
