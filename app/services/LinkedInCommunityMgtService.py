from datetime import datetime, timedelta
import json
from typing import Collection, Dict, Any, List, Optional
from fastapi import BackgroundTasks, HTTPException
from http import HTTPStatus
from fastapi.responses import JSONResponse
import requests
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.helpers.account_tracking_helper import AccountTrackingHelper
from app.core.helpers.linkedin_helper import LinkedinHelper
from app.core.helpers.date_helper import DateHelper
from app.core.helpers.text_helper import TextHelper
from app.domain.adapters.AIPostDataAdapter import AIPostDataAdpater
from app.domain.enums.date_enum import DateFilterEnum
from app.domain.enums.linkedin_enum import (
    LinkedInPostRetrievalOrderEnum,
    LinkedInReactionTypeEnum,
    LinkedInTimeGranularityEnum,
)
from app.domain.enums.socialmediapost_enum import PostPlatformEnum
from app.domain.requests.linkedin_requests import SharePayload, SubscriptionPayload
from app.domain.responses.uri_response import UriResponse
from app.core.config import settings
from app.core.helpers.cache_helper import CacheHelper
from app.repository.CacheRepository import CacheRepository
from urllib.parse import quote

from app.repository.InfluencerRepository import InfluencerRepository
from app.services.AIPostAnalysisService import AIPostAnalysisService
from app.services.EmbeddingService import EmbeddingService


class LinkedInCommunityMgtService:
    BASE_URL = "https://api.linkedin.com/v2"

    @staticmethod
    async def fetch_business_discovery(
        access_token: str,
        organization_id: str,
        db: AsyncIOMotorDatabase,
    ) -> Dict[str, Any]:
        # Generate a cache key based on the URL
        linkedin_user_cache_key = (
            "linkedin_user_cache_key_"
            + CacheHelper.generate_cache_key(organization_id + access_token)
        )

        # Check if cached data exists and is valid
        cached_data = await CacheRepository.get_cache(db, linkedin_user_cache_key)
        if cached_data:
            print("Returning cached data")
            return UriResponse.get_single_data_response(
                "linkedin organization discovery", cached_data
            )

        # Retrieve organization by ID
        organization_response = (
            await LinkedInCommunityMgtService.retrieve_organization_by_id(
                db, organization_id, access_token
            )
        )
        organization_data = LinkedinHelper.extract_relevant_page_data(
            organization_response.get("responseData", None)
        )

        # Retrieve organization follwer count
        follower_count_response = (
            await LinkedInCommunityMgtService.retrieve_organization_follower_count(
                db, organization_id, access_token
            )
        )
        follower_count_data = follower_count_response.get("responseData", None)

        # Retrieve organization posts
        organization_posts_response = (
            await LinkedInCommunityMgtService.get_organization_posts(
                db=db,
                access_token=access_token,
                organization_id=organization_id,
                start=0,
                count=10,
                sort_by=LinkedInPostRetrievalOrderEnum.CREATED,
            )
        )
        organization_posts_data = organization_posts_response.get("responseData", None)

        organization_posts_data_with_engagements = (
            await LinkedInCommunityMgtService.__append_shares_engagement_data(
                db=db,
                access_token=access_token,
                organization_id=organization_id,
                shares=organization_posts_data,
            )
        )

        adapted_posts = await AIPostDataAdpater.adapt_posts(
            organization_posts_data_with_engagements, PostPlatformEnum.LINKEDIN
        )

        influencer_data = (
            (
                await InfluencerRepository.get_influencers_by_filter(
                    db,
                    social_user_id=organization_id,
                    access_token={"ACCOUNT_TRACKING": access_token},
                )
            )
            .get("responseData", {})
            .get("data", [])
        )
        if influencer_data:
            await AccountTrackingHelper.trigger_account_tracking_post_embedding_process(
                db, influencer_data[0], adapted_posts, PostPlatformEnum.LINKEDIN
            )
        combined_data = {
            **organization_data,
            "follower_count": follower_count_data,
            "posts": adapted_posts,
            "linkedin_user_cache_key": linkedin_user_cache_key,
        }

        await CacheRepository.set_cache(
            db=db,
            cache_key=linkedin_user_cache_key,
            data=combined_data,
            ttl=timedelta(hours=9),
        )

        return UriResponse.get_single_data_response(
            "linkedin organization discovery", combined_data
        )

    @staticmethod
    async def create_share_with_company_mention(
        db: AsyncIOMotorDatabase, payload: SharePayload, access_token: Optional[str]
    ) -> Dict[str, Any]:
        url = f"{LinkedInCommunityMgtService.BASE_URL}/shares"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": settings.LINKEDIN_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        }

        response = requests.post(url, json=payload.dict(), headers=headers)
        if response.status_code != HTTPStatus.CREATED:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("message", "Failed to create share."),
            )

        return UriResponse.create_response(
            "Share", response.json(), "Share successfully created."
        )

    @staticmethod
    async def create_subscription_request(
        db: AsyncIOMotorDatabase,
        payload: SubscriptionPayload,
        access_token: Optional[str],
    ) -> Dict[str, Any]:
        url = (
            f"{LinkedInCommunityMgtService.BASE_URL}/eventSubscriptions/"
            "(developerApplication:urn%3Ali%3AdeveloperApplication%3A{application_id},"
            "user:urn%3Ali%3Aperson%3A{person_id},"
            "entity:urn%3Ali%3Aorganization%3A{organization_id},"
            "eventType:ORGANIZATION_SOCIAL_ACTION_NOTIFICATIONS)"
        )

        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": settings.LINKEDIN_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        }

        response = requests.put(url, json=payload.dict(), headers=headers)
        if response.status_code != HTTPStatus.CREATED:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("message", "Failed to create subscription."),
            )

        return UriResponse.create_response(
            "Subscription", response.json(), "Subscription successfully created."
        )

    @staticmethod
    async def retrieve_notifications(
        db: AsyncIOMotorDatabase, access_token: Optional[str]
    ) -> Dict[str, Any]:
        url = f"{LinkedInCommunityMgtService.BASE_URL}/notifications"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": settings.LINKEDIN_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }

        response = requests.get(url, headers=headers)
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("message", "Failed to fetch notifications."),
            )

        return UriResponse.get_list_data_response(
            "Notifications", response.json().get("data", [])
        )

    @staticmethod
    async def remove_subscription(
        db: AsyncIOMotorDatabase, subscription_id: str, access_token: Optional[str]
    ) -> Dict[str, Any]:
        url = f"{LinkedInCommunityMgtService.BASE_URL}/eventSubscriptions/{subscription_id}"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": settings.LINKEDIN_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }

        response = requests.delete(url, headers=headers)
        if response.status_code != HTTPStatus.NO_CONTENT:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("message", "Failed to remove subscription."),
            )

        return UriResponse.delete_response(
            "Subscription",
            is_deleted=True,
            message="Subscription successfully removed.",
        )

    @staticmethod
    async def retrieve_organisation_social_notifications(
        db: AsyncIOMotorDatabase, access_token: Optional[str]
    ) -> Dict[str, Any]:
        url = f"{LinkedInCommunityMgtService.BASE_URL}/eventSubscriptions"
        params = {
            "q": "subscriberAndEventType",
            "eventType": "ORGANIZATION_SOCIAL_ACTION_NOTIFICATIONS",
        }
        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": settings.LINKEDIN_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }

        response = requests.get(url, headers=headers, params=params)
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get(
                    "message", "Failed to retrieve notifications."
                ),
            )

        return UriResponse.get_list_data_response(
            "Notifications", response.json().get("elements", [])
        )

    @staticmethod
    async def __retrieve_follower_statistics_base(
        params: dict,
        access_token: str,
        db: AsyncIOMotorDatabase,
        headers: Optional[dict] = None,
    ):
        url = f"{LinkedInCommunityMgtService.BASE_URL}/organizationalEntityFollowerStatistics"

        headers = headers or {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": settings.LINKEDIN_VERSION,
        }

        cache_key = f"follower-statistics-{CacheHelper.generate_cache_key(params)}"

        cached_follower_statistics = await CacheRepository.get_cache(db, cache_key)
        if cached_follower_statistics:
            print("Returning cached data")
            return cached_follower_statistics

        response = requests.get(url, headers=headers, params=params)
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get(
                    "message", "Failed to retrieve follower statistics."
                ),
            )
        response_data = response.json()
        await CacheRepository.set_cache(db, cache_key=cache_key, data=response_data)
        return response_data

    @staticmethod
    async def retrieve_lifetime_follower_statistics(
        db: AsyncIOMotorDatabase, organization_id: str, access_token: str
    ) -> Dict[str, Any]:
        params = {
            "q": "organizationalEntity",
            "organizationalEntity": f"urn:li:organization:{organization_id}",
        }
        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": settings.LINKEDIN_VERSION,
        }

        response = (
            await LinkedInCommunityMgtService.__retrieve_follower_statistics_base(
                params, access_token, db, headers
            )
        )

        return UriResponse.get_single_data_response(
            "Lifetime Follower Statistics", response
        )

    @staticmethod
    async def retrieve_time_bound_follower_statistics(
        db: Collection,
        organization_id: str,
        access_token: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        date_range: Optional[DateFilterEnum] = None,
        time_granularity: Optional[
            LinkedInTimeGranularityEnum | str
        ] = LinkedInTimeGranularityEnum.DAY,
    ) -> Dict[str, Any]:
        if date_range:
            start_time, end_time = DateHelper.get_date_range(date_range)
        if not start_time or not end_time:
            raise ValueError(
                "start_time or end_time value not provided for time bound follower statistic retrieval"
            )
        params = {
            "q": "organizationalEntity",
            "organizationalEntity": f"urn:li:organization:{organization_id}",
            "timeIntervals.timeGranularityType": time_granularity,
            "timeIntervals.timeRange.start": start_time.timestamp() * 1000,
            "timeIntervals.timeRange.end": end_time.timestamp() * 1000,
        }
        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": settings.LINKEDIN_VERSION,
        }

        response = (
            await LinkedInCommunityMgtService.__retrieve_follower_statistics_base(
                params, access_token, db, headers
            )
        )

        return UriResponse.get_single_data_response(
            "Time-Bound Follower Statistics", response
        )

    @staticmethod
    async def __retrieve_share_statistics_base(
        params: dict,
        access_token: str,
        db: AsyncIOMotorDatabase,
        headers: Optional[dict] = None,
    ) -> requests.Response:
        url = f"{LinkedInCommunityMgtService.BASE_URL}/organizationalEntityShareStatistics"

        headers = headers or {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": settings.LINKEDIN_VERSION,
        }

        cache_key = f"share-statistics-{CacheHelper.generate_cache_key(params)}"

        cached_share_statistics = await CacheRepository.get_cache(db, cache_key)
        if cached_share_statistics:
            print("Returning cached data for share statistics")
            return cached_share_statistics

        response = requests.get(url, headers=headers, params=params)
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get(
                    "message", "Failed to retrieve share statistics."
                ),
            )
        response_data = response.json()
        await CacheRepository.set_cache(db, cache_key=cache_key, data=response_data)
        return response_data

    @staticmethod
    async def retrieve_life_time_share_statistics(
        organization_id: str,
        access_token: str,
        db: AsyncIOMotorDatabase,
    ) -> Dict[str, Any]:
        params = {
            "q": "organizationalEntity",
            "organizationalEntity": f"urn:li:organization:{organization_id}",
        }

        response = await LinkedInCommunityMgtService.__retrieve_share_statistics_base(
            params=params, access_token=access_token, db=db
        )

        return UriResponse.get_single_data_response(
            "Life-time Share Statistics", response
        )

    @staticmethod
    async def retrieve_time_bound_share_statistics(
        db: Collection,
        organization_id: str,
        access_token: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        date_range: Optional[DateFilterEnum] = None,
        time_granularity: Optional[
            LinkedInTimeGranularityEnum | str
        ] = LinkedInTimeGranularityEnum.DAY,
    ) -> Dict[str, Any]:
        if date_range:
            start_time, end_time = DateHelper.get_date_range(date_range)
        if not start_time or not end_time:
            raise ValueError(
                "start_time or end_time value not provided for time bound follower statistic retrieval"
            )
        params = {
            "q": "organizationalEntity",
            "organizationalEntity": f"urn:li:organization:{organization_id}",
            "timeIntervals.timeGranularityType": time_granularity,
            "timeIntervals.timeRange.start": start_time.timestamp() * 1000,
            "timeIntervals.timeRange.end": end_time.timestamp() * 1000,
        }

        response = await LinkedInCommunityMgtService.__retrieve_share_statistics_base(
            params=params, access_token=access_token, db=db
        )

        return UriResponse.get_single_data_response(
            "Time-Bound Share Statistics", response
        )

    @staticmethod
    async def retrieve_life_time_statistics_for_specific_shares(
        organization_id: str,
        share_ids: str,
        access_token: str,
        db: AsyncIOMotorDatabase,
    ) -> Dict[str, Any]:
        share_ids_split = share_ids.split(",")
        params = {
            "q": "organizationalEntity",
            "organizationalEntity": f"urn:li:organization:{organization_id}",
            "shares": [
                f"urn:li:share:{share_id}" for share_id in share_ids_split if share_id
            ],
        }
        response = await LinkedInCommunityMgtService.__retrieve_share_statistics_base(
            params=params, access_token=access_token, db=db
        )

        return UriResponse.get_single_data_response("Share Statistics", response)

    @staticmethod
    async def retrieve_life_time_statistics_for_specific_ugc_posts(
        organization_id: str,
        ugc_post_ids: str,
        access_token: str,
        db: AsyncIOMotorDatabase,
    ) -> Dict[str, Any]:
        ugc_post_ids_split = ugc_post_ids.split(",")

        params = {
            "q": "organizationalEntity",
            "organizationalEntity": f"urn:li:organization:{organization_id}",
        }

        for i in range(len(ugc_post_ids_split)):
            post_id = ugc_post_ids_split[i]
            params[f"ugcPosts[{i}]"] = f"urn:li:ugcPost:{post_id}"

        response = await LinkedInCommunityMgtService.__retrieve_share_statistics_base(
            params=params, access_token=access_token, db=db
        )

        return UriResponse.get_single_data_response("UGC Post Statistics", response)

    @staticmethod
    async def search_by_keyword(
        db: AsyncIOMotorDatabase, organization_id: str, keyword: str, access_token: str
    ) -> Dict[str, Any]:
        from urllib.parse import quote

        url = f"{LinkedInCommunityMgtService.BASE_URL}/peopleTypeahead"
        encoded_organization = quote(f"urn:li:organization:{organization_id}")
        params = {
            "q": "organizationFollowers",
            "keywords": keyword,
            "organization": encoded_organization,
        }
        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": settings.LINKEDIN_VERSION
            or "202302",  # Default to a common version if not set
            "X-Restli-Protocol-Version": "2.0.0",
        }

        print("Request URL:", url)
        print("Request Params:", params)
        print("Request Headers:", headers)

        response = requests.get(url, headers=headers, params=params)

        try:
            response_data = response.json()
        except ValueError:
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Invalid response from LinkedIn API.",
            )

        print("Keyword Result:", response_data)

        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response_data.get("message", "Failed to search by keyword."),
            )

        return UriResponse.get_single_data_response("Search Results", response_data)

    @staticmethod
    async def search_by_vanity_url(
        db: AsyncIOMotorDatabase,
        organization_id: str,
        vanity_url: str,
        access_token: str,
    ) -> Dict[str, Any]:
        url = f"{LinkedInCommunityMgtService.BASE_URL}/vanityUrl"
        params = {
            "q": "vanityUrlAsOrganization",
            "vanityUrl": vanity_url,
            "organization": f"urn:li:organization:{organization_id}",
        }
        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": settings.LINKEDIN_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }

        response = requests.get(url, headers=headers, params=params)
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get(
                    "message", "Failed to search by vanity URL."
                ),
            )

        return UriResponse.get_single_data_response(
            "Vanity URL Search Results", response.json()
        )

    @staticmethod
    async def retrieve_organization_by_id(
        db: AsyncIOMotorDatabase, organization_id: str, access_token: str
    ) -> Dict[str, Any]:
        url = f"{LinkedInCommunityMgtService.BASE_URL}/organizations/{organization_id}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": settings.LINKEDIN_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }

        response = requests.get(url, headers=headers)
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get(
                    "message", "Failed to retrieve organization by ID."
                ),
            )

        response_data = response.json()

        return UriResponse.get_single_data_response(
            "Organization Details", response_data
        )

    @staticmethod
    async def retrieve_organization_follower_count(
        db: AsyncIOMotorDatabase, organization_id: str, access_token: str
    ) -> Dict[str, Any]:
        url = f"{LinkedInCommunityMgtService.BASE_URL}/networkSizes/urn:li:organization:{organization_id}"
        params = {"edgeType": "CompanyFollowedByMember"}
        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": settings.LINKEDIN_VERSION,
        }

        response = requests.get(url, headers=headers, params=params)
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get(
                    "message", "Failed to retrieve follower count."
                ),
            )

        return UriResponse.get_single_data_response("Follower Count", response.json())

    @staticmethod
    async def find_organization_by_email_domain(
        db: AsyncIOMotorDatabase, email_domain: str, access_token: str
    ) -> Dict[str, Any]:
        url = f"{LinkedInCommunityMgtService.BASE_URL}/organizations"
        params = {"q": "emailDomain", "emailDomain": email_domain}
        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": settings.LINKEDIN_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }

        response = requests.get(url, headers=headers, params=params)
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get(
                    "message", "Failed to find organization by email domain."
                ),
            )

        return UriResponse.get_single_data_response(
            "Organization by Email Domain", response.json()
        )

    @staticmethod
    async def retrieve_organization_using_projection(
        db: AsyncIOMotorDatabase,
        organization_id: str,
        projection: str,
        access_token: str,
    ) -> Dict[str, Any]:
        url = f"{LinkedInCommunityMgtService.BASE_URL}/organizations/{organization_id}"
        params = {"projection": projection}
        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": settings.LINKEDIN_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }

        response = requests.get(url, headers=headers, params=params)
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get(
                    "message", "Failed to retrieve organization projection."
                ),
            )

        return UriResponse.get_single_data_response(
            "Organization Projection", response.json()
        )

    @staticmethod
    async def find_non_administered_organization(
        db: AsyncIOMotorDatabase, organization_ids: List[str], access_token: str
    ) -> Dict[str, Any]:
        url = f"{LinkedInCommunityMgtService.BASE_URL}/organizationsLookup"
        params = {"ids": f"List({','.join(organization_ids)})"}
        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": settings.LINKEDIN_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }

        response = requests.get(url, headers=headers, params=params)
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get(
                    "message", "Failed to find non-administered organization."
                ),
            )

        return UriResponse.get_single_data_response(
            "Non-Administered Organizations", response.json()
        )

    @staticmethod
    async def lookup_by_organization_primary_type(
        db: AsyncIOMotorDatabase, organization_id: str, access_token: str
    ) -> Dict[str, Any]:
        url = f"{LinkedInCommunityMgtService.BASE_URL}/organizations/{organization_id}"
        params = {"projection": "(primaryOrganizationType)"}
        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": settings.LINKEDIN_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }

        response = requests.get(url, headers=headers, params=params)
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get(
                    "message", "Failed to lookup by primary organization type."
                ),
            )

        return UriResponse.get_single_data_response(
            "Primary Organization Type", response.json()
        )

    @staticmethod
    async def find_organization_by_vanity_name(
        db: AsyncIOMotorDatabase, vanity_name: str, access_token: str
    ) -> Dict[str, Any]:
        url = f"{LinkedInCommunityMgtService.BASE_URL}/organizations"
        params = {"q": "vanityName", "vanityName": vanity_name}
        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": settings.LINKEDIN_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }

        response = requests.get(url, headers=headers, params=params)
        print("Organisation : ", response.json())
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get(
                    "message", "Failed to find organization by vanity name."
                ),
            )

        return UriResponse.get_single_data_response(
            "Organization by Vanity Name", response.json()
        )

    @staticmethod
    async def batch_get_by_administered_org_ids(
        db: AsyncIOMotorDatabase, organization_ids: List[str], access_token: str
    ) -> Dict[str, Any]:
        url = f"{LinkedInCommunityMgtService.BASE_URL}/organizations"
        params = {"ids": f"List({','.join(organization_ids)})"}
        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": settings.LINKEDIN_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }

        response = requests.get(url, headers=headers, params=params)
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get(
                    "message", "Failed to batch get by administered org IDs."
                ),
            )

        return UriResponse.get_list_data_response(
            "Administered Organizations", response.json().get("elements", [])
        )

    @staticmethod
    async def find_organization_brand_by_vanity_name(
        db: AsyncIOMotorDatabase, vanity_name: str, access_token: str
    ) -> Dict[str, Any]:
        """
        Find an organization brand using its vanity name.
        """
        url = f"{LinkedInCommunityMgtService.BASE_URL}/organizationBrands"
        params = {"q": "vanityName", "vanityName": vanity_name}
        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": settings.LINKEDIN_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }

        response = requests.get(url, headers=headers, params=params)
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get(
                    "message", "Failed to find organization brand by vanity name."
                ),
            )

        return UriResponse.get_single_data_response(
            "Organization Brand", response.json()
        )

    @staticmethod
    async def retrieve_administered_organization_brand(
        db: AsyncIOMotorDatabase, organization_brand_id: str, access_token: str
    ) -> Dict[str, Any]:
        """
        Retrieve an administered organization brand by its ID.
        """
        url = f"{LinkedInCommunityMgtService.BASE_URL}/organizationBrands/{organization_brand_id}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": settings.LINKEDIN_VERSION,
        }

        response = requests.get(url, headers=headers)
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get(
                    "message", "Failed to retrieve administered organization brand."
                ),
            )

        return UriResponse.get_single_data_response(
            "Administered Organization Brand", response.json()
        )

    @staticmethod
    async def batch_get_on_administered_organization_brands(
        db: AsyncIOMotorDatabase, organization_brand_ids: List[str], access_token: str
    ) -> Dict[str, Any]:
        """
        Batch GET on Administered Organization Brands.
        """
        url = f"{LinkedInCommunityMgtService.BASE_URL}/organizationBrands"
        params = {"ids": f"List({','.join(organization_brand_ids)})"}
        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": settings.LINKEDIN_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }

        response = requests.get(url, headers=headers, params=params)
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get(
                    "message",
                    "Failed to batch get on administered organization brands.",
                ),
            )

        return UriResponse.get_list_data_response(
            "Administered Organization Brands", response.json().get("elements", [])
        )

    @staticmethod
    async def batch_get_on_non_administered_organization_brands(
        db: AsyncIOMotorDatabase, organization_brand_ids: List[str], access_token: str
    ) -> Dict[str, Any]:
        """
        Batch GET on Non-Administered Organization Brands.
        """
        url = f"{LinkedInCommunityMgtService.BASE_URL}/organizationBrandsLookup"
        params = {"ids": f"List({','.join(organization_brand_ids)})"}
        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": settings.LINKEDIN_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }

        response = requests.get(url, headers=headers, params=params)
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get(
                    "message",
                    "Failed to batch get on non-administered organization brands.",
                ),
            )

        return UriResponse.get_list_data_response(
            "Non-Administered Organization Brands", response.json().get("elements", [])
        )

    @staticmethod
    async def find_administered_organization_brands_by_parent_org(
        db: AsyncIOMotorDatabase, parent_organization_id: str, access_token: str
    ) -> Dict[str, Any]:
        """
        Find Administered Organization Brands by Parent Organization.
        """
        url = f"{LinkedInCommunityMgtService.BASE_URL}/organizations"
        params = {
            "q": "parentOrganization",
            "parent": f"urn:li:organization:{parent_organization_id}",
        }
        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": settings.LINKEDIN_VERSION,
        }

        response = requests.get(url, headers=headers, params=params)
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get(
                    "message",
                    "Failed to find administered organization brands by parent organization.",
                ),
            )

        return UriResponse.get_list_data_response(
            "Administered Organization Brands by Parent Organization",
            response.json().get("elements", []),
        )

    @staticmethod
    async def find_member_organization_access_control(
        db: AsyncIOMotorDatabase, access_token: str
    ) -> Dict[str, Any]:
        """
        Find a member's organization access control.
        """
        url = f"{LinkedInCommunityMgtService.BASE_URL}/organizationAcls"
        params = {"q": "roleAssignee"}
        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": settings.LINKEDIN_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }

        response = requests.get(url, headers=headers, params=params)
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get(
                    "message", "Failed to find member's organization access control."
                ),
            )

        return UriResponse.get_list_data_response(
            "Organization Access Controls", response.json().get("elements", [])
        )

    @staticmethod
    async def find_organization_administrators(
        db: AsyncIOMotorDatabase, organization_id: str, access_token: str
    ) -> Dict[str, Any]:
        """
        Find organization administrators.
        """
        url = f"{LinkedInCommunityMgtService.BASE_URL}/organizationAcls"
        params = {
            "q": "organization",
            "organization": f"urn:li:organization:{organization_id}",
            "role": "ADMINISTRATOR",
            "state": "APPROVED",
        }
        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": settings.LINKEDIN_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }

        response = requests.get(url, headers=headers, params=params)
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get(
                    "message", "Failed to find organization administrators."
                ),
            )

        return UriResponse.get_list_data_response(
            "Organization Administrators", response.json().get("elements", [])
        )

    @staticmethod
    async def find_organization_access_control(
        db: AsyncIOMotorDatabase, organization_id: str, access_token: str
    ) -> Dict[str, Any]:
        """
        Find organization access control.
        """
        url = f"{LinkedInCommunityMgtService.BASE_URL}/organizationAcls"
        params = {
            "q": "organization",
            "organization": f"urn:li:organization:{organization_id}",
        }
        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": settings.LINKEDIN_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }

        response = requests.get(url, headers=headers, params=params)
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get(
                    "message", "Failed to find organization access control."
                ),
            )

        return UriResponse.get_list_data_response(
            "Organization Access Control", response.json().get("elements", [])
        )

    @staticmethod
    async def get_organization_posts(
        db: AsyncIOMotorDatabase,
        organization_id: List[str] | str,
        access_token: str,
        start: int,
        count: int,
        sort_by: LinkedInPostRetrievalOrderEnum,
    ) -> Dict[str, Any]:
        encoded_urn = f"urn%3Ali%3Aorganization%3A{organization_id}"
        url = f"{LinkedInCommunityMgtService.BASE_URL}/ugcPosts?q=authors&authors=List({encoded_urn})&start={start}&count={count}&sortBy={sort_by.value}"
        cache_key = CacheHelper.generate_cache_key(url)

        cached_data = await CacheRepository.get_cache(db, cache_key=cache_key)
        if cached_data:
            print("Returning cached data for linkedin posts")
            return cached_data

        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": settings.LINKEDIN_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
            "X-RestLi-Method": "FINDER",
        }

        response = requests.get(url, headers=headers)
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get(
                    "message", "Failed to get user or organization posts."
                ),
            )
        response = UriResponse.get_list_data_response(
            "LinkedIn post", response.json().get("elements", [])
        )
        try:
            await CacheRepository.set_cache(db, cache_key=cache_key, data=response)
        except Exception as e:
            print(f"Error setting cache for linkedin posts: {e}")

        return response

    @staticmethod
    async def get_comments_for_a_share(
        share_id: str,
        access_token: str,
    ) -> Dict[str, Any]:
        encoded_urn = f"urn%3Ali%3Ashare%3A{share_id}"

        url = f"{LinkedInCommunityMgtService.BASE_URL}/socialActions/{encoded_urn}/comments"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": settings.LINKEDIN_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }

        response = requests.get(url, headers=headers)
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("message", "Failed to get share comments."),
            )

        return UriResponse.get_list_data_response(
            "Share comment", response.json().get("elements", [])
        )

    @staticmethod
    async def get_reactions_for_a_share(
        share_urn: str,
        access_token: str,
        sort: LinkedInReactionTypeEnum = LinkedInReactionTypeEnum.REVERSE_CHRONOLOGICAL,
        start: int = 0,
        count: int = 10,
    ) -> Dict[Any, str]:
        encoded_urn = quote(share_urn)
        url = f"https://api.linkedin.com/rest/reactions/(entity:{encoded_urn})"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": settings.LINKEDIN_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }
        print(headers)
        params = {"q": "entity", "sort": sort.value, "start": start, "count": count}

        response = requests.get(url=url, headers=headers, params=params)

        if response.status_code != HTTPStatus.OK:
            print(
                f"\nException getting share reactions: {response.status_code} -> {response.text}"
            )
            return UriResponse.get_single_data_response("reactions", None)

        return UriResponse.get_list_data_response("reaction", response.json())

    @staticmethod
    async def fetch_ai_post_report(db: AsyncIOMotorDatabase, cache_key: str) -> dict:
        media_report_cache_key = "linkedin-ai-post-media-report-" + cache_key

        # Check if cached data exists and is valid
        report_cached_data = await CacheRepository.get_cache(
            db, media_report_cache_key
        )  # ---- DB CALL
        if report_cached_data:
            print("Returning cached data")
            return UriResponse.get_single_data_response(
                "ai media report", report_cached_data
            )  # ---- O(1)

        cached_post_data = await CacheRepository.get_cache(db, cache_key)
        if not cached_post_data:
            return UriResponse.get_single_data_response(
                "posts for media ai report", None
            )  # ---- DB CALL (Consider using redis for caching)

        MAX_POSTS = 25
        full_posts = cached_post_data.get("posts", [])
        posts = full_posts[:MAX_POSTS]

        try:
            if len(posts) > 0:
                final_response = await AIPostAnalysisService.generate_ai_post_report(
                    posts
                )  # ---- Call to AI

                final_response["hashtag_mention_frequency"] = (
                    TextHelper.compute_hashtag_frequency(full_posts, "content")
                )

                # Cache response for 24 hours
                await CacheRepository.set_cache(
                    db, media_report_cache_key, final_response, ttl=timedelta(hours=24)
                )

                return UriResponse.get_single_data_response(
                    "ai media report", final_response
                )
            else:
                return UriResponse.get_single_data_response(
                    "ai media report",
                    {},
                    "Can't generate AI media report for an account with no posts",
                )
        except (json.JSONDecodeError, KeyError, AttributeError):
            return UriResponse.get_single_data_response(
                "ai media report", None, code=500, message="Failed to parse AI response"
            )

    @staticmethod
    async def __append_shares_engagement_data(
        db: Collection, access_token: str, organization_id: str, shares: List[dict]
    ) -> List[dict]:
        share_ids: list = []
        aggregated_dict: dict = {}
        temp_dict: dict = {}
        for share in shares:
            share_urn = share.get("id", "")
            share_id = share_urn.split(":")[-1]
            share_ids.append(share_id)
        joined_share_ids = ",".join(share_ids)

        share_statistics_response = await LinkedInCommunityMgtService.retrieve_life_time_statistics_for_specific_shares(
            db=db,
            organization_id=organization_id,
            share_ids=joined_share_ids,
            access_token=access_token,
        )

        share_statistics = share_statistics_response.get("responseData", {}).get(
            "elements"
        )

        for i in range(len(shares)):
            share = shares[i]
            share_id = share.get("id")

            if i < len(share_statistics):
                share_statistic = share_statistics[i].get("totalShareStatistics", {})
                share_statistic_id = share_statistic.get("share")
            else:
                share_statistic = {
                    "uniqueImpressionsCount": 0,
                    "shareCount": 0,
                    "engagement": 0,
                    "clickCount": 0,
                    "likeCount": 0,
                    "impressionCount": 0,
                    "commentCount": 0,
                }

            # Add share to aggregated dict
            aggregated_dict[share_id] = share

            # If the shareID is in the temporary dictionary (which means its equivalent
            # post statistics are already in the dictionary)
            if share_id in temp_dict.keys():
                aggregated_dict[share_id]["engagement_summary"] = temp_dict[share_id]

            # If share statistic ID is in the aggregated dictionary (which means its
            # equivalent post is already in the dictionary)
            if share_statistic_id and share_statistic_id in aggregated_dict.keys():
                aggregated_dict[share_statistic_id][
                    "engagement_summary"
                ] = share_statistic
            elif not share_statistic_id and share_id in aggregated_dict.keys():
                aggregated_dict[share_id]["engagement_summary"] = share_statistic
            else:
                if share_statistic_id:
                    temp_dict[share_statistic_id] = share_statistic
                else:
                    temp_dict[share_id] = share_statistic
        shares = list(aggregated_dict.values())

        for share in shares:
            if share.get("engagement_summary"):
                print("\nShare: ", share)

        print("\nAggregated_dict: ", aggregated_dict)
        return shares
