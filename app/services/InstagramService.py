from datetime import datetime, timedelta
import json
from http import HTTPStatus
import time
from urllib import response
from fastapi.responses import JSONResponse
import requests
from app.core.helpers.account_tracking_helper import AccountTrackingHelper
from app.core.helpers.instagram_helper import InstagramHelper
from app.core.helpers.reportgeneration_helper import ReportGenerationHelper
from app.core.helpers.text_helper import TextHelper
from app.domain.adapters.MentionAdapter import MentionAdapter
from app.domain.enums.date_enum import DateFilterEnum

from app.domain.enums.endpoints_enum import EndpointsEnum
from app.domain.enums.instagram_enum import (
    InstagramMediaContainerStatusEnum,
    InstagramMediaTypeEnum,
    InstagramMetricTypeEnum,
    InstagramPeriodEnum,
)
from app.domain.enums.socialmediapost_enum import PostPlatformEnum
from app.domain.models.reportgeneration_model import ReportMetadataModel
from app.domain.requests.instagram_requests import PostInstagramMediaRequest
from app.domain.requests.reportgeneration_requests import ReportGenerationRequest
from app.domain.schemas.mention_schema import MentionCreate
from app.repository.InstagramRepository import InstagramRepository
from app.repository.InfluencerRepository import InfluencerRepository
from app.core.config import settings
from app.domain.responses.uri_response import UriResponse
from app.domain.models.instagram_model import InstagramBatchRequestData
from app.domain.models.chat_model import (
    InsightSummary,
    InstagramCommentKeyword,
)
from app import schemas
from typing import Any, Dict, Optional, List
from urllib.parse import urlencode
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repository.MentionRepository import MentionRepository
from app.services.AIPostAnalysisService import AIPostAnalysisService
from app.services.EmbeddingService import EmbeddingService
from app.services.FeatureLimitService import FeatureLimitService
from app.services.AIService import AIService
from app.domain.enums import ai_prompt
from app.repository.CacheRepository import CacheRepository
from app.core.helpers.cache_helper import CacheHelper
from app.domain.schemas import influencer_schema
from app.domain.enums.account_enum import AccountTypeEnum
from app.core.cache.manager.cache_manager import CacheManager
from app.services.SentimentService import SentimentService


class InstagramService:
    CACHE_TTL = timedelta(hours=2)  # Set cache expiration time (e.g., 1 hour)
    cache_service = CacheManager.get_cache_service

    @staticmethod
    def get_user_data(access_token: str):
        url = f"https://graph.facebook.com/{settings.INSTAGRAM_API_VERSION}/me?fields=id,name,accounts,businesses&access_token={access_token}"

        response = requests.get(url)

        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code, detail=response.json()
            )
        return response.json()

    @staticmethod
    async def save_instagram_account(
        user_id: str,
        access_token: str,
        db: AsyncIOMotorDatabase,
        account_limits: dict,
    ):
        url = f"https://graph.facebook.com/{settings.INSTAGRAM_API_VERSION}/me/accounts?fields=id,access_token,name,picture,username,instagram_business_account%7Bid,username,biography,profile_picture_url%7D&access_token={access_token}"

        instagram_limit = account_limits.get("instagram_limit", 0)
        facebook_limit = account_limits.get("facebook_limit", 0)
        total_accounts_limit = account_limits.get("accounts_limit", 0)
        instagram_count = 0
        facebook_count = 0

        try:
            response = requests.get(url)
        except:
            raise

        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code, detail=response.json()
            )

        pages_data = response.json().get("data", [])
        if not pages_data:
            # No Facebook Pages found — fall back to saving the user's personal Facebook profile
            me_url = f"https://graph.facebook.com/{settings.INSTAGRAM_API_VERSION}/me?fields=id,name,picture&access_token={access_token}"
            try:
                me_response = requests.get(me_url)
                if me_response.status_code == HTTPStatus.OK:
                    me_data = me_response.json()
                    personal_influencer = influencer_schema.InfluencerCreate(
                        user_id=user_id,
                        social_name=me_data.get("name", ""),
                        profile_pic=me_data.get("picture", {}).get("data", {}).get("url", ""),
                        account_type=AccountTypeEnum.PROFESSIONAL,
                        social_user_id=me_data.get("id", ""),
                        social_username=me_data.get("name", ""),
                        social_platform="FACEBOOK",
                        connected=True,
                        token=access_token,
                    )
                    save_result = await InfluencerRepository.create_or_update_influencer(db, personal_influencer)
                    if save_result.get("success"):
                        await FeatureLimitService.sync_specific_feature_limit_for_user(
                            db, user_id, EndpointsEnum.SAVE_FACEBOOK_ACCOUNTS.value, "FACEBOOK"
                        )
                    return await InfluencerRepository.get_influencers_by_filter(db, user_id)
            except Exception as e:
                print(f"Error saving personal Facebook account: {e}")
            return UriResponse.get_single_data_response("instagram account", None)

        # Save Facebook user pages
        pages = schemas.FacebookUserPagesCreate(user_id=user_id, data=pages_data)
        data = await InstagramRepository.create_facebook_user_pages(db=db, pages=pages)

        if not data:
            return UriResponse.get_single_data_response("instagram account", None)

        influencers: List[influencer_schema.InfluencerCreate] = []

        count = 0
        while count < len(pages_data):
            page = pages_data[count]
            # Handle Instagram business accounts
            instagram_business_account = page.get("instagram_business_account")

            if instagram_business_account and (
                instagram_count < instagram_limit
            ):
                influencers.append(
                    influencer_schema.InfluencerCreate(
                        user_id=user_id,
                        social_name=page.get("name", ""),
                        profile_pic=instagram_business_account.get(
                            "profile_picture_url", ""
                        ),
                        account_type=AccountTypeEnum.PROFESSIONAL,
                        social_user_id=instagram_business_account.get("id", ""),
                        social_username=instagram_business_account.get("username", ""),
                        social_platform="INSTAGRAM",
                        connected=True,
                        token=access_token,
                        meta_access_token=access_token,
                    )
                )
                instagram_count += 1

            # Handle Facebook accounts
            if (
                page.get("id")
                and (facebook_count < facebook_limit)
            ):
                influencers.append(
                    influencer_schema.InfluencerCreate(
                        user_id=user_id,
                        social_name=page.get("name", ""),
                        bio=page.get("bio", ""),
                        profile_pic=page.get("picture", {})
                        .get("data", {})
                        .get("url", ""),
                        account_type=AccountTypeEnum.PROFESSIONAL,
                        social_user_id=page.get("id", ""),
                        social_username=page.get("username") or page.get("name", ""),
                        social_platform="FACEBOOK",
                        connected=True,
                        token=page.get("access_token", ""),
                    )
                )
                facebook_count += 1

            # Stop if we've reached the total limit or both individual limits
            if (instagram_count + facebook_count) >= total_accounts_limit:
                break

            count += 1

        # Save all influencers
        if influencers:
            platform_to_endpoint = {
                PostPlatformEnum.INSTAGRAM.value: EndpointsEnum.SAVE_INSTAGRAM_ACCOUNTS.value,
                PostPlatformEnum.FACEBOOK.value: EndpointsEnum.SAVE_FACEBOOK_ACCOUNTS.value,
            }
            for influencer in influencers:
                save_result = await InfluencerRepository.create_or_update_influencer(
                    db, influencer
                )
                if not save_result.get("success"):
                    print(f"Error saving influencer: {influencer.social_username}")
                else:
                    platform = influencer.social_platform
                    if platform:
                        platform_key = platform.value if hasattr(platform, 'value') else platform
                        endpoint = platform_to_endpoint.get(platform_key, "")
                        await FeatureLimitService.sync_specific_feature_limit_for_user(
                            db,
                            user_id,
                            endpoint,
                            platform,
                        )

        return await InfluencerRepository.get_influencers_by_filter(db, user_id)

    @staticmethod
    async def fetch_auth_business_discovery(
        db: AsyncIOMotorDatabase,
        username: str,
        access_token: str,
        before: Optional[str] = None,
        after: Optional[str] = None,
        limit: int = 24,
    ):
        """
        Fetch Instagram Business Discovery data using a *user* access token by calling:
        GET /me/accounts?fields=...instagram_business_account{...media{...}}...

        Fixes:
        - Avoids `business_account` being referenced before assignment.
        - Removes duplicated business_account lookup blocks.
        - Ensures paging `next_url` is a string URL (not `{}`).
        - Returns proper error responses when Graph returns non-200.
        """

        # Base URL for Instagram business account details with media records
        url = InstagramService._set_auth_business_discovery_params(
        access_token, before, after, limit
    )

        # Generate a cache key based on the URL
        cache_key = CacheHelper.generate_cache_key(url)

        # Check if cached data exists and is valid
        cached_data = await CacheRepository.get_cache(db, cache_key)
        if cached_data:
            print("Returning cached data")
            return UriResponse.get_single_data_response("business", cached_data)

        # Make the initial request to the API
        response = requests.get(url)
        response_data = response.json()

        # If Graph returned an error, bubble it up properly
        if response.status_code != HTTPStatus.OK:
            print("API Error:", response_data)
            return UriResponse.custom_response(
            message="Facebook Graph error while fetching /me/accounts",
            error_code=response.status_code,
            success=False,
            data=response_data,
        )

        # Extract pages data
        data_response = response_data.get("data", [])
        if not data_response:
            return UriResponse.error_response(
            "No Facebook Pages/Instagram business accounts found for this access token."
        )

        # Find the page whose instagram_business_account.username matches the requested username
        page_match = next(
        (
            item
            for item in data_response
            if (item.get("instagram_business_account") or {}).get("username") == username
        ),
        None,
    )

        # Pull out the instagram business account object
        business_account = (page_match or {}).get("instagram_business_account") or {}
        if not business_account:
            return UriResponse.error_response(
            "This IG account is not linked to any Page accessible by this token (or it’s not a professional account)."
            )

        # Media + paging
        media_obj = business_account.get("media") or {}
        media_data = media_obj.get("data") or []

        paging_info = media_obj.get("paging") or {}
        after_cursor = (paging_info.get("cursors") or {}).get("after")
        next_url = paging_info.get("next")  # should be a URL string if present

        # If there is an after cursor and next URL, fetch the next batch
        if after_cursor and next_url:
            next_response = requests.get(next_url)
            next_response_data = next_response.json()

        if next_response.status_code == HTTPStatus.OK:
            next_media_data = next_response_data.get("data") or []
            if next_media_data:
                media_data.extend(next_media_data)

            # Replace paging with the newest paging
            if "media" not in business_account:
                business_account["media"] = {}
            business_account["media"]["paging"] = next_response_data.get("paging")
        else:
            print("Next page API Error:", next_response_data)

        # Fetch influencer record (optional) and trigger embedding
        influencer_data = (
        (
            await InfluencerRepository.get_influencers_by_filter(
                db=db, social_username=username, access_token=access_token
            )
        )
        .get("responseData", {})
        .get("data", [])
    )

        if influencer_data:
            await AccountTrackingHelper.trigger_account_tracking_post_embedding_process(
            db, influencer_data[0], media_data, PostPlatformEnum.INSTAGRAM
        )

        # Return merged media + cache key
        if "media" not in business_account:
            business_account["media"] = {}

        business_account["media"]["data"] = media_data
        business_account["cache_key"] = cache_key

        # Cache the fresh response
        await CacheRepository.set_cache(db, cache_key, business_account, ttl=timedelta(hours=2))

        return UriResponse.get_single_data_response("business", business_account)

    @staticmethod
    async def fetch_batch_business_discovery(
        ig_usernames: List[str],
        before: Optional[str] = None,
        after: Optional[str] = None,
    ):
        # Set default fields if fields are None
        fields = "id,ig_id,username,biography,website,profile_picture_url,followers_count,follows_count,media_count,media%7Bcomments_count,like_count,media_type,media_url,timestamp,permalink,caption%7D"

        batch: List[InstagramBatchRequestData] = []
        for username in ig_usernames:
            relative_url = f"/{settings.INSTAGRAM_BUSINESS_ID}?fields=business_discovery.username({username})%7B{fields}%7D"

            if after:
                relative_url += f"&after={after}"

            batch.append(
                InstagramBatchRequestData(method="GET", relative_url=relative_url)
            )

        batch_response = await InstagramService.batch_requests(
            data=batch, access_token=settings.META_SYSTEM_TOKEN
        )

        result = []
        for res in batch_response:
            if "body" in res:
                data = json.loads(res["body"])
                print("API Response:", data)  # Debugging log
                if "business_discovery" in data:
                    result.append(data["business_discovery"])
                else:
                    print("Key 'business_discovery' not found in response:", data)
                    raise HTTPException(
                        status_code=400,
                        detail="Key 'business_discovery' missing in API response",
                    )

        return UriResponse.get_single_data_response("business", result)

    @staticmethod
    async def fetch_anonymous_business_discovery(
        db: AsyncIOMotorDatabase,
        username: str,
        before: Optional[str] = None,
        after: Optional[str] = None,
    ):
        # Set default fields if fields are None
        url = InstagramService._set_anon_business_discovery_params(
            username, before, after
        )

        print(url)

        # Generate a cache key based on the URL
        cache_key = CacheHelper.generate_cache_key(url)

        print("Cache Key : ", cache_key)
        # Check if cached data exists and is valid
        cached_data = await CacheRepository.get_cache(db, cache_key)
        if cached_data:
            print("Returning cached data")
            return UriResponse.get_single_data_response("business", cached_data)

        response = requests.get(url)

        if response.status_code != HTTPStatus.OK:
            print("API Error:", response.json())  # Log error details
            return UriResponse.get_single_data_response("business", None)

        result = response.json()
        data = result["business_discovery"]

        media_data = data.get("media", {}).get("data", [])

        data["media"]["data"] = media_data

        data["cache_key"] = cache_key

        # Cache the fresh response with the provided TTL
        await CacheRepository.set_cache(db, cache_key, data, ttl=timedelta(hours=2))
        return UriResponse.get_single_data_response("business", data)

    @staticmethod
    async def fetch_business_discovery(
        db: AsyncIOMotorDatabase,
        username: str,
        access_token: Optional[str] = None,
    ):
        import os
        if os.getenv("LOCAL_DEV_MODE", "").lower() in ["true", "1", "yes"]:
            print(f"🔧 LOCAL DEV: Bypassing subscription validation for Instagram business discovery")
            # Continue with normal flow - no subscription check needed
        try:
            if access_token and username:
                # TO DO: Add comment sentiments before returning data
                discovery = (
                    await InstagramService.fetch_auth_business_discovery(
                        db, username, access_token
                    )
                ).get("responseData", {})
            elif username:
                discovery = (
                    await InstagramService.fetch_anonymous_business_discovery(
                        db, username
                    )
                ).get("responseData", {})
            else:
                raise HTTPException(
                    status_code=400,
                    detail="username or access_token required",
                )

            if discovery:
                media_data = discovery.get("media", {}).get("data", [])

                media_data = [
                    {
                        "engagements_count": media.get("comments_count", 0)
                        + media.get("like_count", 0),
                        **media,
                    }
                    for media in media_data
                ]

                discovery["media"]["data"] = media_data

                return UriResponse.get_single_data_response(
                    "instagram business discovery", discovery
                )
            raise Exception("Failed to get your account info")

        except HTTPException as e:
            print("An error occurred while fetching your business discovery: ", e)
            if e.status_code == 401 or e.status_code == 403:
                status_code = 400
            return JSONResponse(status_code=status_code, content={"message": e.detail})
        except Exception as e:
            print("Exception occurred in fetching your business discovery: ", e)
            return UriResponse.error_response(
                "An error occurred while fetching your business discovery"
            )

    @staticmethod
    async def batch_requests(data: List[InstagramBatchRequestData], access_token: str):
        base_url = f"https://graph.facebook.com/{settings.INSTAGRAM_API_VERSION}"

        batch_data = []
        for req in data:
            batch_data.append(
                f"%7B'method':'{req.method}','relative_url':'{req.relative_url}'%7D"
            )

        full_url = f"{base_url}?batch=[{','.join(batch_data)}]&include_headers=false&access_token={access_token}"

        # Log the full URL for debugging
        print("Batch Request URL:", full_url)

        response = requests.post(full_url)

        if response.status_code != HTTPStatus.OK:
            print("API Error:", response.json())  # Log error details
            raise HTTPException(
                status_code=response.status_code, detail=response.json()
            )

        return response.json()

    @staticmethod
    async def fetch_instagram_media_insights(
        media_id: str,
        metrics: Optional[str],
        access_token: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        breakdown: Optional[str] = None,
    ):

        base_url = f"https://graph.facebook.com/{settings.INSTAGRAM_API_VERSION}/{media_id}/insights"
        print("Access Token:", access_token)
        print("Base URL:", base_url)

        params = {"metric": metrics}

        if breakdown:
            params["breakdown"] = breakdown
        if since:
            params["since"] = since
        if until:
            params["until"] = until

        query_string = urlencode(params)
        full_url = f"{base_url}?{query_string}&access_token={access_token}"

        response = requests.get(full_url)

        if response.status_code != HTTPStatus.OK:
            print(response.json())
            return UriResponse.get_single_data_response(
                "media insight", None, code=response.status_code
            )

        result = response.json()

        # Log the response data for debugging purposes
        print("Instagram Insights Data: ", json.dumps(result, indent=2))

        # Ensure that result contains 'data' key
        if "data" not in result:
            return UriResponse.get_single_data_response(
                "media insight",
                None,
                code=500,
                message="Missing 'data' key in Instagram response",
            )

        insights_data = result["data"]

        # Generate the AI prompt using the updated method
        prompt = (
            ai_prompt.AIChiefAnalystPrompt.USER_MEDIA_INSIGHTS_REQUEST.value.format(
                insights_data=insights_data
            )
        )

        # Prepare the AI request using system and user prompts
        ai_request = AIService.build_ai_model(
            messages=[{"role": "user", "content": prompt}]
        )

        # Get AI-generated report
        ai_report = await AIService.chat_completion(ai_request)

        # Correctly access the AI response content
        try:
            # Accessing choices and content properly
            ai_report_content = (
                ai_report.choices[0].message.content.strip("```json").strip()
            )
            ai_report_json = json.loads(ai_report_content)
        except (json.JSONDecodeError, KeyError, AttributeError) as e:
            print(f"Error parsing AI response: {e}")
            return UriResponse.get_single_data_response(
                "media insight", None, code=500, message="Failed to parse AI response"
            )

        print("AI Report : ", ai_report_json)

        # Combine the Instagram media insights data with the AI-generated report
        combined_result = {"insights": result["data"], "ai_report": ai_report_json}

        return UriResponse.get_single_data_response("media insight", combined_result)

    @staticmethod
    async def fetch_instagram_user_insights(
        instagram_user_id: Optional[str],
        metrics: Optional[str],
        period: Optional[str],
        user_facebook_access_token: str,
        metric_type: Optional[str] = "total_value",
        timeframe: Optional[str] = None,
        since: Optional[str] = None,
        breakdown: Optional[str] = None,
        until: Optional[str] = None,
    ):

        base_url = f"https://graph.facebook.com/{settings.INSTAGRAM_API_VERSION}/{instagram_user_id}/insights"

        params = {"metric": metrics, "period": period, "metric_type": metric_type}

        if since:
            params["since"] = since
        if until:
            params["until"] = until
        if timeframe:
            params["timeframe"] = timeframe
        if breakdown:
            params["breakdown"] = breakdown

        # Encode the parameters, but exclude the access_token
        query_string = urlencode(params)

        # Manually append the access_token at the end
        full_url = (
            f"{base_url}?{query_string}&access_token={user_facebook_access_token}"
        )

        print("Insight Full Url : ", full_url)

        response = requests.get(full_url)

        print("Insight Response : ", response.json())

        if response.status_code != HTTPStatus.OK:
            print(response.json())
            return UriResponse.get_single_data_response(
                "insights", None, code=response.status_code
            )

        result = response.json()

        return UriResponse.get_single_data_response("user insight", result["data"])

    @staticmethod
    async def fetch_instagram_user_insights_interaction_metrics(
        ig_user_id: Optional[str],
        metrics: Optional[str],
        metric_type: Optional[str],
        period: Optional[str],
        breakdown: Optional[str] = None,
        user_facebook_access_token: str = "",
        since: Optional[str | datetime] = None,
        until: Optional[str | datetime] = None,
    ):

        base_url = f"https://graph.facebook.com/{settings.INSTAGRAM_API_VERSION}/{ig_user_id}/insights"

        params: Dict[str, Any] = {
            "metric": metrics,
        }
        if period:
            params["period"] = period
        if metric_type:
            params["metric_type"] = metric_type
        if breakdown:
            params["breakdown"] = breakdown
        if since:
            params["since"] = since
        if until:
            params["until"] = until

        # Encode the parameters, but exclude the access_token
        query_string = urlencode(params)

        # Manually append the access_token at the end
        full_url = (
            f"{base_url}?{query_string}&access_token={user_facebook_access_token}"
        )

        response = requests.get(full_url)

        if response.status_code != HTTPStatus.OK:
            print(response.json())
            return UriResponse.get_single_data_response(
                "insights", None, code=response.status_code
            )

        result = response.json()

        return UriResponse.get_single_data_response(
            "user interaction insight", result["data"]
        )

    @staticmethod
    async def fetch_instagram_demographic_metrics(
        ig_user_id: Optional[str],
        metrics: Optional[str],
        metric_type: Optional[str],
        breakdowns: Optional[str],
        period: Optional[str],
        timeframe: Optional[str],
        user_facebook_access_token: str,
        since: Optional[str | datetime] = None,
        until: Optional[str | datetime] = None,
    ):
        """
        Fetches Instagram demographic metrics for the specified IG user.

        Metric: engaged_audience_demographics
        - The demographic characteristics of the engaged audience, including countries, cities, and gender distribution.
        - This data provides insights into the distribution of audience engagement by age, city, country, and gender.
        - The following timeframes can be used:
            - last_14_days, last_30_days, last_90_days, prev_month, this_month, this_week
            - Note: The last_14_days, last_30_days, last_90_days, and prev_month timeframes will no longer be supported
            beginning with v20.0. See the changelog for more information.
        - `this_month` returns data from the last 30 days, and `this_week` returns data from the last 7 days.
        - The data will not be returned if the IG user has less than 100 engagements during the selected timeframe.

        **Parameters:**
        - `ig_user_id`: The Instagram user ID for which metrics are to be fetched.
        - `metrics`: The metrics to retrieve (e.g., engaged_audience_demographics).
        - `metric_type`: Specifies the type of the metric (e.g., total_value).
        - `breakdowns`: Breakdown of demographics (e.g., age, city, country, gender).
        - `period`: The period of the metric (e.g., lifetime).
        - `timeframe`: The timeframe for the demographic data (e.g., last_30_days, this_week).
        - `user_facebook_access_token`: Facebook user access token to authenticate the API call.
        - `since`: Optional start date in UNIX timestamp format (not supported for this metric).
        - `until`: Optional end date in UNIX timestamp format (not supported for this metric).

        **Note:**
        - `since` and `until` parameters are not applicable for the engaged_audience_demographics metric, as this metric does
        not support custom date ranges. It only accepts predefined timeframes like this_week and this_month.

        **Returns:**
        - A dictionary containing demographic insights or an error response if the request fails.
        """

        base_url = f"https://graph.facebook.com/{settings.INSTAGRAM_API_VERSION}/{ig_user_id}/insights"

        # Set up the parameters for the API call
        params: Dict[str, Any] = {
            "metric": metrics,
            "period": period,
            "timeframe": timeframe,
            "metric_type": metric_type,
            "breakdown": breakdowns,
        }

        # Although 'since' and 'until' are not used for this metric, checking and adding them in case of future use
        if since:
            params["since"] = since
        if until:
            params["until"] = until

        # Encode the parameters, excluding the access_token
        query_string = urlencode(params)

        # Append the access_token manually
        full_url = (
            f"{base_url}?{query_string}&access_token={user_facebook_access_token}"
        )

        # Make the API request
        response = requests.get(full_url)

        # Handle non-OK responses
        if response.status_code != HTTPStatus.OK:
            return UriResponse.get_single_data_response(
                "demography insight", None, code=response.status_code
            )

        # Return the resulting data
        result = response.json()

        return UriResponse.get_single_data_response(
            "demography insight", result["data"]
        )

    @staticmethod
    async def fetch_instagram_business_tags(
        access_token: str, ig_user_id: str, after: Optional[str]
    ):
        url = f"https://graph.facebook.com/{settings.INSTAGRAM_API_VERSION}/{ig_user_id}/tags?fields=id,media_type,instagram_business_account,username,engagement,comments,comments_count,like_count,permalink,caption,media_url,timestamp&access_token={access_token}"

        if after:
            url = f"{url}&after={after}"

        response = requests.get(url)

        if response.status_code != HTTPStatus.OK:
            return UriResponse.get_single_data_response(
                "media", None, code=response.status_code
            )

        result = response.json()

        paging_info = result.get("paging", {})

        print("Mentions Result : ", result)

        # Variables to store overall sentiment data
        total_feedback = 0
        positive_score = 0.0
        neutral_score = 0.0
        negative_score = 0.0
        sentiment_distribution = {"positive": 0, "neutral": 0, "negative": 0}
        top_positive = None
        top_negative = None

        analyzed_data = []

        # Analyze sentiment for each media item
        for media in result.get("data", []):
            caption = media.get("caption", "")

            if caption:
                try:
                    sentiment = await AIService.analyze_sentiment(caption)
                    sentiment_score = sentiment.get("score", 0)
                    sentiment_magnitude = sentiment.get("magnitude", 0)

                    # Classify sentiment as Positive, Neutral, or Negative
                    if sentiment_score > 0:
                        sentiment_label = "Positive"
                        positive_score += sentiment_score
                        sentiment_distribution["positive"] += 1
                    elif sentiment_score < 0:
                        sentiment_label = "Negative"
                        negative_score += sentiment_score
                        sentiment_distribution["negative"] += 1
                    else:
                        sentiment_label = "Neutral"
                        neutral_score += 1
                        sentiment_distribution["neutral"] += 1

                    total_feedback += 1

                    # Track top positive and top negative posts
                    if sentiment_score > 0 and (
                        not top_positive or sentiment_score > top_positive["score"]
                    ):
                        top_positive = {
                            "id": media["id"],
                            "caption": caption,
                            "media_type": media["media_type"],
                            "username": media["username"],
                            "permalink": media["permalink"],
                            "score": sentiment_score,
                            "magnitude": sentiment_magnitude,
                        }
                    elif sentiment_score < 0 and (
                        not top_negative or sentiment_score < top_negative["score"]
                    ):
                        top_negative = {
                            "id": media["id"],
                            "caption": caption,
                            "media_type": media["media_type"],
                            "username": media["username"],
                            "permalink": media["permalink"],
                            "score": sentiment_score,
                            "magnitude": sentiment_magnitude,
                        }

                    # Add sentiment label and sentiment data to the media item
                    media["sentiment"] = {
                        "label": sentiment_label,
                        "score": sentiment_score,
                        "magnitude": sentiment_magnitude,
                    }

                except Exception as e:
                    media["sentiment"] = {
                        "error": str(e)
                    }  # Handle any potential errors in sentiment analysis
            else:
                media["sentiment"] = {
                    "label": "Neutral",  # Default label if no caption
                    "score": None,
                    "magnitude": None,
                }

            analyzed_data.append(media)

        # Now calculate the percentage for each sentiment type
        if total_feedback > 0:
            positive_percentage = (
                sentiment_distribution["positive"] / total_feedback
            ) * 100
            neutral_percentage = (
                sentiment_distribution["neutral"] / total_feedback
            ) * 100
            negative_percentage = (
                sentiment_distribution["negative"] / total_feedback
            ) * 100
        else:
            positive_percentage = neutral_percentage = negative_percentage = 0

        # Ensure the percentages sum to 100% (handling potential rounding issues)
        remaining_percentage = 100 - (
            positive_percentage + neutral_percentage + negative_percentage
        )
        if remaining_percentage > 0:
            if positive_percentage > 0:
                positive_percentage += remaining_percentage
            elif neutral_percentage > 0:
                neutral_percentage += remaining_percentage
            else:
                negative_percentage += remaining_percentage

        # Construct the overall sentiment object
        overall_sentiment = {
            "total_feedback": total_feedback,
            "positive_score": positive_score,
            "neutral_score": neutral_score,
            "negative_score": negative_score,
            "sentiment_distribution": {
                "positive": positive_percentage,
                "neutral": neutral_percentage,
                "negative": negative_percentage,
            },
            "top_positive": top_positive,
            "top_negative": top_negative,
        }

        return {
            "status": True,
            "responseCode": 200,
            "responseMessage": "Tags successfully retrieved.",
            "responseData": {
                "posts": analyzed_data,
                "overall_sentiment": overall_sentiment,
                "paging": paging_info,
            },
        }

    @staticmethod
    async def fetch_business_stories(access_token: str, ig_user_id: str):
        url = f"https://graph.facebook.com/{settings.INSTAGRAM_API_VERSION}/{ig_user_id}/stories?fields=id,media_type,instagram_business_account,username,comments_count,like_count,permalink,caption,media_url,timestamp&access_token={access_token}"

        response = requests.get(url)

        print("Stories Response : ", response.json())

        if response.status_code != HTTPStatus.OK:
            return UriResponse.get_single_data_response(
                "stories", None, code=response.status_code
            )

        result = response.json()

        return UriResponse.get_single_data_response("stories", result["data"])

    @staticmethod
    async def fetch_business_media(
        access_token: str, ig_user_id: str, next: Optional[str] = None
    ):
        url = f"https://graph.facebook.com/{settings.INSTAGRAM_API_VERSION}/{ig_user_id}/media?fields=id,media_type,username,comments_count,like_count,permalink,caption,media_url,timestamp,comments%7Bid,text,username,timestamp,replies%7D&access_token={access_token}"

        if next:
            url = next

        response = requests.get(url)

        print("Media Response : ", response.json())

        if response.status_code != HTTPStatus.OK:
            return UriResponse.get_single_data_response(
                "media", None, code=response.status_code
            )

        result = response.json()

        return UriResponse.get_single_data_response("media", result)

    @staticmethod
    async def fetch_business_mentioned_comment(
        access_token: str, ig_user_id: str, comment_id: str
    ):
        url = f"https://graph.facebook.com/{settings.INSTAGRAM_API_VERSION}/{ig_user_id}?fields=mentioned_comment.comment_id({comment_id})%7Bid,like_count,media,text,timestamp%7D&access_token={access_token}"

        response = requests.get(url)

        print("Mentions Response : ", response)
        if response.status_code != HTTPStatus.OK:
            return UriResponse.get_single_data_response(
                "comment", None, code=response.status_code
            )

        result = response.json()

        return UriResponse.get_single_data_response("comment", result)

    @staticmethod
    async def fetch_business_media_mentions(
        ig_user_id: str, media_id: str, access_token: str
    ):
        base_url = (
            f"https://graph.facebook.com/{settings.INSTAGRAM_API_VERSION}/{ig_user_id}"
        )

        full_url = f"{base_url}?fields=mentioned_media.media_id({media_id})%7Bid,media_type,comments,comments_count,like_count,caption,media_url,timestamp%7D&access_token={access_token}"

        response = requests.get(full_url)

        print("Media Mentions : ", response.json())

        if response.status_code != HTTPStatus.OK:
            return UriResponse.get_single_data_response(
                "media", None, code=response.status_code
            )

        result = response.json()

        return UriResponse.get_single_data_response("media", result["mentioned_media"])

    @staticmethod
    async def fetch_business_media_comments(ig_media_id: str, access_token: str):
        base_url = f"https://graph.facebook.com/{settings.INSTAGRAM_API_VERSION}/{ig_media_id}/comments"

        full_url = f"{base_url}?fields=from%7Bid,username%7D,hidden,id,like_count,media_type,parent_id,replies,text,timestamp,media,user,username&access_token={access_token}"

        response = requests.get(full_url)

        print("Comments : ", response.json())

        if response.status_code != HTTPStatus.OK:
            return UriResponse.get_single_data_response(
                "comment", None, code=response.status_code
            )

        result = response.json()

        return UriResponse.get_single_data_response("media", result["data"])

    @staticmethod
    async def fetch_business_comment_replies(ig_comment_id: str, access_token: str):
        base_url = f"https://graph.facebook.com/{settings.INSTAGRAM_API_VERSION}/{ig_comment_id}"

        full_url = f"{base_url}?fields=from,hidden,id,like_count,media_type,parent_id,replies,text,timestamp,media_url,user,username%&access_token={access_token}"

        response = requests.get(full_url)

        print("Comment Replies : ", response.json())

        if response.status_code != HTTPStatus.OK:
            return UriResponse.get_single_data_response(
                "comment", None, code=response.status_code
            )

        result = response.json()

        return UriResponse.get_single_data_response("media", result["mentioned_media"])

    @staticmethod
    async def fetch_hashtag_search(
        keyword: str,
        fields: Optional[
            str
        ] = "id,media_type,comments_count,like_count,caption,media_url,timestamp",
        since: Optional[str] = None,
        until: Optional[str] = None,
        after: Optional[str] = None,
        access_token: Optional[str] = None,
    ):
        if not access_token:
            access_token = settings.META_SYSTEM_TOKEN

        hashtag_response = requests.get(
            f"https://graph.facebook.com/ig_hashtag_search?q={keyword}&user_id={settings.INSTAGRAM_BUSINESS_ID}&access_token={access_token}"
        )

        if hashtag_response.status_code != HTTPStatus.OK:
            return UriResponse.get_single_data_response(
                "hashtag", None, code=HTTPStatus.NOT_FOUND
            )

        hashtag = hashtag_response.json()

        # Access the id value, handling null checks
        id_value = hashtag["data"]  # Get the 'data' list, defaulting to an empty list.
        if id_value:
            id_value = id_value[0][
                "id"
            ]  # Get the 'id' value from the first element, handling potential None
        else:
            return UriResponse.get_single_data_response(
                "hashtag", None, code=HTTPStatus.NOT_FOUND
            )

        media_url = f"https://graph.facebook.com/{id_value}/top_media?user_id={settings.INSTAGRAM_BUSINESS_ID}&fields={fields}&access_token={settings.META_SYSTEM_TOKEN}"

        if after:
            media_url += f"&after={after}"

        media_response = requests.get(media_url)

        if media_response.status_code != HTTPStatus.OK:
            return UriResponse.get_single_data_response(
                "media", None, code=media_response.status_code
            )

        result = media_response.json()

        return UriResponse.get_single_data_response("media", result["data"])

    @staticmethod
    async def track_keyword(
        keyword: str,
        access_token: str,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ):
        if not access_token:
            access_token = settings.META_SYSTEM_TOKEN
            ig_user_id = settings.INSTAGRAM_BUSINESS_ID
        else:
            ig_user = await InstagramService.get_user_data(access_token)
            ig_user_id = ig_user["id"]

        media = (
            await InstagramService.fetch_hashtag_search(
                keyword=keyword, access_token=access_token, since=since, until=until
            )
        ).dict()
        if media["status"] == True and len(media["responseData"]) > 0:
            media = media["responseData"]
        else:
            return UriResponse.get_single_data_response(
                "results", None, code=HTTPStatus.NOT_FOUND
            )

        total_posts = len(media)
        total_impressions = []
        total_reach = []
        total_engagement = []
        total_sentiments = {"total": 0, "positive": 0, "neutral": 0, "negative": 0}

        for post in media:
            # sentiment = SentimentService.analyze_sentiment(
            #     post["caption"]
            # )
            # total_sentiments["total"] += 1
            # if sentiment == "positive":
            #     total_sentiments["positive"] += 1
            # if sentiment == "neutral":
            #     total_sentiments["neutral"] += 1
            # if sentiment == "negative":
            #     total_sentiments["negative"] += 1

            if media["media_type"] == "IMAGE":
                metrics = "reach,impressions,engagement"
            else:
                metrics = "reach"

            insights = await InstagramService.fetch_instagram_media_insights(
                media_id=media["id"],
                access_token=access_token,
                metrics=metrics,
                since=since,
                until=until,
            )

            if media["media_type"] == "IMAGE":
                total_reach.append(insights["responseData"][0]["values"])
                total_impressions.append(insights["responseData"][1]["values"])
                total_engagement.append(insights["responseData"][2]["values"])
            else:
                total_reach.append(insights["responseData"][0]["values"])

        result = {
            "insights": {
                "total": total_posts,
                "impressions": total_impressions,
                "reach": total_reach,
                "engagement": total_engagement,
                "sentiments": total_sentiments,
            },
            "media": media,
        }

        return UriResponse.get_single_data_response("media", result)

    @staticmethod
    async def save_instagram_insights(
        user_id: str, ig_user_id: str, data: dict, db: AsyncIOMotorDatabase
    ):
        insights_data = schemas.InstagramInsightsCreate(
            user_id=user_id, ig_user_id=ig_user_id, data=data
        )
        db_insights = await InstagramRepository.create_instagram_insights(
            db=db, insights=insights_data
        )
        print("Instagram insights saved: ", db_insights)
        return schemas.InstagramInsights(**db_insights)

    @staticmethod
    async def get_instagram_insights(
        user_id: str, ig_user_id: str, db: AsyncIOMotorDatabase
    ) -> Any:
        collection = db["instagram_insights"]
        insights = await collection.find_one(
            {"user_id": user_id, "ig_user_id": ig_user_id}
        )
        if not insights:
            raise HTTPException(status_code=404, detail="Insights not found")
        return insights

    @staticmethod
    async def update_instagram_insights(
        user_id: str, ig_user_id: str, data: dict, db: AsyncIOMotorDatabase
    ):
        collection = db["instagram_insights"]
        result = await collection.update_one(
            {"user_id": user_id, "ig_user_id": ig_user_id},
            {"$set": {"data": data}},
            upsert=True,
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Insights not found")
        return {"message": "Instagram insights updated successfully"}

    @staticmethod
    async def delete_instagram_insights(
        user_id: str, ig_user_id: str, db: AsyncIOMotorDatabase
    ):
        collection = db["instagram_insights"]
        result = collection.delete_one({"user_id": user_id, "ig_user_id": ig_user_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Insights not found")
        return {"message": "Instagram insights deleted successfully"}

    @staticmethod
    async def fetch_ai_post_report(db: AsyncIOMotorDatabase, cache_key: str) -> dict:
        media_report_cache_key = "instagram-ai-post-media-report-" + cache_key

        # Check cached data
        report_cached_data = await CacheRepository.get_cache(db, media_report_cache_key)
        if report_cached_data:
            return UriResponse.get_single_data_response(
                "ai media report", report_cached_data
            )

        cached_post_data = await CacheRepository.get_cache(db, cache_key)
        if not cached_post_data:
            return UriResponse.get_single_data_response(
                "posts for media ai report", None
            )

        full_posts = cached_post_data["media"]["data"]

        # Limit posts to avoid excessive token usage
        MAX_POSTS = 25
        EXCLUDED_FIELDS = ["id", "comments", "permalink", "media_url"]

        posts = [
            {k: v for k, v in post.items() if k not in EXCLUDED_FIELDS}
            for post in full_posts[:MAX_POSTS]
        ]

        try:
            if len(posts) > 0:
                final_response = await AIPostAnalysisService.generate_ai_post_report(
                    posts
                )  # ---- Call to AI

                final_response["hashtag_mention_frequency"] = (
                    TextHelper.compute_hashtag_frequency(full_posts, "caption")
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
        except (json.JSONDecodeError, KeyError, AttributeError) as e:
            print(e)
            return UriResponse.get_single_data_response(
                "ai media report", None, code=500, message="Failed to parse AI response"
            )

    @staticmethod
    async def fetch_ai_post_report_v1(db: AsyncIOMotorDatabase, cache_key: str) -> dict:
        media_report_cache_key = "instagram-ai-post-media-report-" + cache_key

        # Check if cached data exists and is valid
        report_cached_data = await CacheRepository.get_cache(db, media_report_cache_key)
        if report_cached_data:
            print("Returning cached data")
            return UriResponse.get_single_data_response(
                "ai media report", report_cached_data
            )

        cached_post_data = await CacheRepository.get_cache(db, cache_key)
        if not cached_post_data:
            return UriResponse.get_single_data_response(
                "posts for media ai report", None
            )

        full_posts = cached_post_data["media"]["data"]

        posts = []

        for post in full_posts:
            # Creating a new dictionary without 'permalink' and 'media_url'
            filtered_media = {
                k: v
                for k, v in post.items()
                if k not in ["id", "comments", "permalink", "media_url"]
            }

            # Append filtered media data to the processed list
            posts.append(filtered_media)

        print("Parsed Posts : ", posts)
        prompt = ai_prompt.AIChiefAnalystPrompt.INSTAGRAM_POST_INSIGHTS_SUMMARY_REQUEST.value.format(
            posts=posts[:25]
        )
        model = AIService.build_ai_model(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )

        ai_report = (
            await AIService.structured_chat_completion(model, InsightSummary)
        ).dict()
        # print(ai_report)

        try:
            # Accessing choices and content properly
            ai_report_content = ai_report["choices"][0]["message"]["parsed"]
            print(ai_report_content)

            # Cache the fresh response with the provided TTL
            await CacheRepository.set_cache(
                db, media_report_cache_key, ai_report_content, ttl=timedelta(hours=24)
            )
            return UriResponse.get_single_data_response(
                "ai media report", ai_report_content
            )
        except (json.JSONDecodeError, KeyError, AttributeError) as e:
            print(f"Error parsing AI response: {e}")
            return UriResponse.get_single_data_response(
                "ai media report", None, code=500, message="Failed to parse AI response"
            )

    @staticmethod
    async def __create_media_container(
        ig_user_id: str,
        media_url: str,
        media_type: InstagramMediaTypeEnum,
        caption: str,
        access_token: str,
    ):
        url = f"https://graph.facebook.com/v22.0/{ig_user_id}/media"

        params = {
            "caption": caption,
            "access_token": access_token,
        }

        if media_type == InstagramMediaTypeEnum.IMAGE:
            params["image_url"] = media_url
        else:
            params["media_type"] = media_type.value
            params["video_url"] = media_url

        response = requests.post(url, params=params)
        print("\nResponse from creating media container: ", response)
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code, detail=response.json()
            )
        return response.json()

    @staticmethod
    async def __check_media_container_status(
        container_id: str, access_token: str
    ) -> Optional[str]:
        url = f"https://graph.facebook.com/v22.0/{container_id}?fields=status_code"

        headers = {"Authorization": f"Bearer {access_token}"}

        response = requests.get(url, headers=headers)
        print("Response from checking media container status: ", response.json())
        if response.status_code == HTTPStatus.OK:
            response_data = response.json()
            media_container_status = response_data.get("status_code", None)
            if not media_container_status:
                raise ValueError("Error checking media container status")
            return media_container_status
        else:
            print(f"{response.status_code} error: {response.text}")
            return None

    @staticmethod
    async def __publish_media_container(
        ig_user_id: str, container_id: str, access_token: str
    ):
        url = f"https://graph.facebook.com/v22.0/{ig_user_id}/media_publish"

        params = {
            "creation_id": container_id,
            "access_token": access_token,
        }

        response = requests.post(url, params=params)

        if response.status_code != HTTPStatus.OK:
            return UriResponse.custom_response(
                error_code=response.status_code, success=False, data=response.json()
            )

        return UriResponse.create_response("instagram post", data=response.json())

    @staticmethod
    async def publish_media_post(
        ig_user_id: str, payload: PostInstagramMediaRequest, access_token: str
    ):
        print("Function posting started")
        create_container_response = await InstagramService.__create_media_container(
            ig_user_id=ig_user_id,
            media_url=payload.media_url,
            media_type=payload.media_type,
            caption=payload.caption,
            access_token=access_token,
        )
        print("Container created successfully: ", create_container_response)
        container_id = create_container_response.get("id", None)
        if not container_id:
            raise ValueError("Container ID not gotten successfully")
        max_retries = 5
        default_error_response = UriResponse.create_response("instagram post", None)

        try:
            instagram_post_response = await InstagramService.__retry_post_logic(
                max_retries=max_retries,
                default_error_response=default_error_response,
                container_id=container_id,
                access_token=access_token,
                ig_user_id=ig_user_id,
            )
            return instagram_post_response
        except Exception as e:
            return UriResponse.error_response(
                f"Exception occurred in posting instagram media: {e}"
            )

    @staticmethod
    async def __retry_post_logic(
        max_retries: int,
        default_error_response: Dict[Any, str],
        container_id: str,
        access_token: str,
        ig_user_id: str,
    ):
        retries = 0
        while retries < max_retries:
            media_container_status = (
                await InstagramService.__check_media_container_status(
                    container_id=container_id, access_token=access_token
                )
            )
            if (
                media_container_status
                == InstagramMediaContainerStatusEnum.FINISHED.value
                or media_container_status
                == InstagramMediaContainerStatusEnum.ERROR.value
            ):
                return await InstagramService.__publish_media_container(
                    ig_user_id=ig_user_id,
                    container_id=container_id,
                    access_token=access_token,
                )
            elif (
                media_container_status
                == InstagramMediaContainerStatusEnum.EXPIRED.value
            ):
                return UriResponse.error_response(
                    "The container was not published within 24 hours and has expired."
                )
            elif (
                media_container_status
                == InstagramMediaContainerStatusEnum.PUBLISHED.value
            ):
                return UriResponse.custom_response(
                    "Media container has already been published",
                    error_code=200,
                    success=True,
                )
            time.sleep(60)
            retries += 1
        return default_error_response

    @staticmethod
    async def fetch_mentioned_comment(
        access_token: str, ig_user_id: str, comment_id: str
    ):
        """
        Fetches data on an IG Comment where the user was mentioned.

        :param access_token: User's Instagram access token.
        :param ig_user_id: Instagram user ID.
        :param comment_id: ID of the comment where the user was mentioned.
        :return: Response containing mentioned comment data or an error.
        """
        url = (
            f"https://graph.facebook.com/{settings.INSTAGRAM_API_VERSION}/{ig_user_id}"
        )
        params = {
            "fields": f"mentioned_comment.comment_id({comment_id}){{id,like_count,media,text,timestamp}}",
            "access_token": access_token,
        }

        response = requests.get(url, params=params)

        if response.status_code != HTTPStatus.OK:
            print("Error fetching mentioned comment:", response.json())
            return UriResponse.get_single_data_response(
                "mentioned_comment", None, code=response.status_code
            )

        result = response.json()
        return UriResponse.get_single_data_response("mentioned_comment", result)

    @staticmethod
    async def fetch_cached_instagram_posts(
        db: AsyncIOMotorDatabase, ig_username: str, user_message: str
    ) -> dict:
        influencer = await InfluencerRepository.get_influencer_by_username(
            db, ig_username
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
            db, page_id, PostPlatformEnum.INSTAGRAM.value, user_message
        )

        return UriResponse.get_single_data_response(
            "instagram posts for ai report", posts
        )

    @staticmethod
    def _set_auth_business_discovery_params(
        access_token,
        before: Optional[str] = None,
        after: Optional[str] = None,
        limit: Optional[int] = 24,
    ):
        url = (
            f"https://graph.facebook.com/{settings.INSTAGRAM_API_VERSION}/me/accounts"
            f"?fields=id,name,instagram_business_account%7Bid,ig_id,username,biography,website,"
            f"profile_picture_url,followers_count,follows_count,media_count,media"
            f"%7Bcomments_count,like_count,media_type,media_url,timestamp,permalink,caption,comments%7Bid,text,username,timestamp,replies%7D%7D%7D"
            f"&limit={limit}&access_token={access_token}"
        )

        # Add pagination parameters if available
        if before:
            url += f"&before={before}"
        elif after:
            url += f"&after={after}"
        return url

    @staticmethod
    def _set_anon_business_discovery_params(
        username: str, before=Optional[None], after=Optional[None]
    ):
        fields = "id,ig_id,username,biography,website,profile_picture_url,followers_count,follows_count,media_count,media%7Bcomments_count,like_count,media_type,media_url,timestamp,permalink,caption%7D"

        url = f"https://graph.facebook.com/{settings.INSTAGRAM_BUSINESS_ID}?fields=business_discovery.username({username})%7B{fields}%7D&access_token={settings.META_SYSTEM_TOKEN}"

        if after:
            url = f"{url}&after={after}"
        if before:
            url = f"{url}&before={before}"
        return url

    @staticmethod
    async def process_mentions_from_webhook(
        db: AsyncIOMotorDatabase, webhook_data: dict
    ):
        # Extract user ids, media ids and comment ids from webhook data
        ids_data = await InstagramHelper.extract_ids_from_webhook(webhook_data)  # O(n)

        if not ids_data:
            print("No data gotten from mentions")
            return None

        # Cache influencer data to avoid redundant database queries
        influencer_cache = {}

        # Group media IDs to reduce API calls
        media_comments_cache = {}

        for social_user_id, value in ids_data.items():  # O(n)
            if social_user_id not in influencer_cache:
                influencer_data = (
                    await InfluencerRepository.get_influencer_by_social_user_id(
                        db, social_user_id
                    )
                ).get("responseData")
                if not influencer_data:
                    print(f"Error getting influencer data for {social_user_id}")
                    continue
                influencer_cache[social_user_id] = influencer_data

            influencer_data = influencer_cache[social_user_id]
            access_token = influencer_data.get("token")
            media_id = value.get("media_id")
            comment_id = value.get("comment_id")

            if not access_token:
                continue

            # Fetch comments in bulk for the same media_id
            if media_id not in media_comments_cache:
                user_comments = (
                    await InstagramService.fetch_business_media_comments(
                        media_id, access_token
                    )
                ).get("responseData", [])
                user_comments = {item.get("id"): item for item in user_comments}
                media_comments_cache[media_id] = user_comments

            mentioned_comment = media_comments_cache[media_id].get(comment_id)
            comment_text = mentioned_comment.get("text", "")
            ai_generated_keyword_result = (
                await InstagramService.generate_keyword_from_comment(comment_text)
            )
            if not ai_generated_keyword_result:
                keyword = ""
            else:
                keyword = ai_generated_keyword_result.get("keyword")

            sentiment_data = await AIService.analyze_sentiment(comment_text)

            ids_data[social_user_id] = {
                **value,
                "influencer_data": influencer_data,
                "comment_data": mentioned_comment,
                "keyword": keyword,
                "sentiment": SentimentService.select_sentiment(
                    sentiment_data.get("sentiment", "neutral")
                ),
                "sentiment_score": sentiment_data.get("score"),
            }

        processed_data_for_mention_creation = []

        for data in list(ids_data.values()):
            processed_data_for_mention_creation += data

        # Mentions to be created
        processed_mentions_data = MentionAdapter.adapt_instagram_comment_to_mention(
            processed_data_for_mention_creation
        )

        if not processed_mentions_data:
            print("Webhook data adaptation to mentions data failed")
            return None
        # Create multiple mentions
        try:
            response = await MentionRepository.multiple_create_mentions(
                db=db,
                mentions=[
                    MentionCreate(**mention_data)
                    for mention_data in processed_mentions_data
                ],
            )
            return response
        except Exception as e:
            print("Exception occurred in creating mentions from webhooks: ", e)
            return None

    @staticmethod
    async def generate_keyword_from_comment(
        comment: str,
    ) -> Optional[InstagramCommentKeyword]:
        if not comment:
            print("Comment text not available for keyword generation")
            return None

        prompt = f"""
            Consider the following comment gotten from Instagram;
            {comment}.
            Analyze the text and highlight a single keyword to completely capture the main point or topic of the comment.
        """

        model = AIService.build_ai_model(
            messages=[
                {
                    "role": "user",
                    "content": f"{prompt}",
                }
            ]
        )

        try:
            ai_response = (
                await AIService.structured_chat_completion(
                    model, InstagramCommentKeyword
                )
            ).dict()

            response = ai_response["choices"][0]["message"]["parsed"]

            # Return the parsed summary directly
            return response
        except Exception as e:
            # Log issues for debugging
            print(f"Error while generating keyword: {e}")
            return None

    @staticmethod
    async def generate_raw_metadata_for_report_gen(
        db: AsyncIOMotorDatabase, report_generation_data: ReportGenerationRequest
    ):
        if (
            not report_generation_data.influencer_ids
            or not report_generation_data.influencer_ids.instagram
        ):
            raise ValueError(
                "Influencer ID not provided for instagram account tracking report gen"
            )
        token, social_id, username = await ReportGenerationHelper.get_influencer_data(
            db,
            report_generation_data.influencer_ids.instagram,
            report_generation_data.user_id,
        )
        start_date, end_date, previous_start = (
            ReportGenerationHelper.calculate_date_range(report_generation_data.period)
        )

        try:
            current_period_insights = (
                await InstagramService.generate_insights_for_report_gen(
                    token,
                    social_id,
                    report_generation_data.period,
                    start_date,
                    end_date,
                )
            )
            previous_period_insights = (
                await InstagramService.generate_insights_for_report_gen(
                    token,
                    social_id,
                    report_generation_data.period,
                    previous_start,
                    start_date,
                )
            )
            instagram_account_info_response = (
                await InstagramService.fetch_auth_business_discovery(
                    access_token=token, db=db, username=username
                )
            )
            if not instagram_account_info_response.get("status"):
                raise ValueError("No instagram account found for this user")
            instagram_account_info = instagram_account_info_response.get("responseData")
            if len(instagram_account_info.get("media", {}).get("data")) == 0:
                raise ValueError(
                    "No posts to analyze for instagram account tracking report generation."
                )

            metadata = ReportMetadataModel(
                account_info=instagram_account_info,
                current_period_insights=current_period_insights,
                previous_period_insights=previous_period_insights,
                since=start_date,
                until=end_date,
            ).dict(exclude_none=True)
            return metadata
        except Exception as e:
            print("Error occurred in getting instagram metadata: ", e)
            raise

    @staticmethod
    async def generate_insights_for_report_gen(
        token: str,
        instagram_user_id: str,
        timeframe: DateFilterEnum,
        since: datetime,
        until: datetime,
    ):
        # Ensure date range is at most 30 days
        if (until - since).days > 30:
            since = until - timedelta(days=30)

        insights = []
        # Get impressions(reach) data
        impression_metrics = (
            await InstagramService.fetch_instagram_user_insights_interaction_metrics(
                ig_user_id=instagram_user_id,
                metrics="reach",
                metric_type=InstagramMetricTypeEnum.TIME_SERIES.value,
                period=InstagramPeriodEnum.DAY.value,
                user_facebook_access_token=token,
                since=since,
                until=until,
            )
        )

        if impression_metrics.get("status"):
            impression_metrics_data = impression_metrics.get("responseData")
            insights.extend(impression_metrics_data)

        # Get engagements data
        engagement_metrics = (
            await InstagramService.fetch_instagram_user_insights_interaction_metrics(
                ig_user_id=instagram_user_id,
                metrics="follows_and_unfollows",
                metric_type=InstagramMetricTypeEnum.TOTAL_VALUE.value,
                period=InstagramPeriodEnum.DAY.value,
                user_facebook_access_token=token,
                since=since,
                until=until,
            )
        )

        if engagement_metrics.get("status"):
            engagement_metrics_data = engagement_metrics.get("responseData")
            insights.extend(engagement_metrics_data)

        demographic_metrics = (
            await InstagramService.fetch_instagram_demographic_metrics(
                ig_user_id=instagram_user_id,
                metrics="follower_demographics",
                metric_type=InstagramMetricTypeEnum.TOTAL_VALUE.value,
                breakdowns="country",
                timeframe=InstagramHelper.map_datefilter_enum_to_timeframe_enum(
                    timeframe
                ).value,
                period=InstagramPeriodEnum.LIFETIME.value,
                user_facebook_access_token=token,
            )
        )

        if demographic_metrics.get("status"):
            demographic_metrics_data = demographic_metrics.get("responseData")
            insights.append(
                demographic_metrics_data[0]
                .get("total_value", {})
                .get("breakdowns", [])[0]
                .get("results", [])
            )

        return insights
