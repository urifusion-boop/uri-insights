from http import HTTPStatus
import json
from fastapi.responses import JSONResponse
import requests
from app.core.config import settings
from app.core.helpers.account_tracking_helper import AccountTrackingHelper
from app.core.helpers.facebook_helper import FacebookHelper
from app.core.helpers.file_helper import FileHelper
from app.core.helpers.reportgeneration_helper import ReportGenerationHelper
from app.core.helpers.text_helper import TextHelper
from app.domain.adapters.AIPostDataAdapter import AIPostDataAdpater
from app.domain.enums.socialmediapost_enum import PostPlatformEnum
from app.domain.models.reportgeneration_model import ReportMetadataModel
from app.domain.requests.reportgeneration_requests import ReportGenerationRequest
from app.domain.responses.uri_response import UriResponse
from app.domain.models.meta_model import MetaBatchRequestData
from typing import Any, Dict, Optional, List
from urllib.parse import urlencode  # Importing urlencode
from fastapi import HTTPException
from app.domain.requests.facebook_requests import (
    FacebookInsightsParameters,
    FacebookMultipleMediaPayload,
    FacebookPostPayload,
    FacebookUpdatePostPayload,
    FacebookPhotoPayload,
    FacebookUploadFile,
    FacebookVideoPayload,
    FacebookReelVideoPayload,
)
from app.services.AIPostAnalysisService import AIPostAnalysisService
from app.services.AIService import AIService
from app.domain.enums import ai_prompt
from app.domain.models import chat_model
from app.repository.CacheRepository import CacheRepository
from app.core.helpers.cache_helper import CacheHelper
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase

import time
from app.repository.InfluencerRepository import InfluencerRepository
from app.services.EmbeddingService import EmbeddingService


class FacebookService:
    @staticmethod
    def get_user_data(access_token: str):
        url = f"https://graph.facebook.com/{settings.FACEBOOK_API_VERSION}/me?fields=id,name&access_token={access_token}"

        response = requests.get(url)

        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code, detail=response.json()
            )

        return response.json()

    @staticmethod
    async def get_user_accounts(access_token: str):
        if not access_token:
            access_token = settings.META_SYSTEM_TOKEN

        url = f"https://graph.facebook.com/{settings.FACEBOOK_API_VERSION}/me/accounts?fields=id,name,access_token&access_token={access_token}"

        response = requests.get(url)

        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code, detail=response.json()
            )

        result = response.json()

        return UriResponse.get_list_data_response("pages", result)

    @staticmethod
    async def fetch_facebook_page_discovery(
        page_id: str,
        access_token: str,
        db: AsyncIOMotorDatabase,
        before: Optional[str] = None,
        after: Optional[str] = None,
        fields: Optional[
            str
        ] = "id,name,followers_count,fan_count,about,link,username,verification_status,description,engagement,location,bio,website,company_overview,picture{url}",
    ):
        """
        Fetch detailed discovery data for a specific Facebook Page.

        **Parameters**:
        - `page_id`: The ID of the Facebook Page.
        - `access_token`: Access token with permissions for the page.
        - `fields`: Fields to include in the response (default includes name, fan_count, engagement, etc.).
        - `limit`: Number of items per page.
        - `before`: Pagination cursor for previous page.
        - `after`: Pagination cursor for next page.
        - `db`: AsyncIOMotorDatabase instance for caching.

        **Returns**:
        - Detailed Facebook page data or an error response.
        """
        try:
            base_url, params, full_params = (
                FacebookService._set_facebook_discovery_request(
                    page_id, access_token, before, after, fields
                )
            )
            # Generate cache key based on URL
            cache_key = CacheHelper.generate_cache_key(full_params)

            # Check for cached data
            cached_data = await CacheRepository.get_cache(db, cache_key)
            if cached_data:
                print("Returning cached data")
                return UriResponse.get_single_data_response(
                    "page_discovery", cached_data
                )

            # Request the data from Facebook API
            response = requests.get(base_url, params=params)

            if response.status_code != HTTPStatus.OK:
                error_message = (
                    response.json().get("error", {}).get("message", "Unknown error")
                )
                print(f"Facebook API Error: {error_message}")
                return UriResponse.get_single_data_response(
                    "page_discovery",
                    None,
                    error_message,
                    code=response.status_code,
                )

            result = response.json()

            post_response = await FacebookService.fetch_facebook_page_posts(
                access_token
            )

            if post_response:
                adapted_post_data = await AIPostDataAdpater.adapt_posts(
                    post_response.get("responseData", {})
                    .get("feed", {})
                    .get("data", []),
                    PostPlatformEnum.FACEBOOK,
                )
                result["post_data"] = adapted_post_data
                influencer_data = (
                    (
                        await InfluencerRepository.get_influencers_by_filter(
                            db=db, social_user_id=page_id, access_token=access_token
                        )
                    )
                    .get("responseData", {})
                    .get("data", [])
                )
                if influencer_data:
                    await AccountTrackingHelper.trigger_account_tracking_post_embedding_process(
                        db,
                        influencer_data[0],
                        adapted_post_data,
                        PostPlatformEnum.FACEBOOK,
                    )
            # Cache the data
            await CacheRepository.set_cache(
                db,
                cache_key,
                {**result, "facebook_cache_key": cache_key},
                ttl=timedelta(hours=2),
            )

            return UriResponse.get_single_data_response(
                "facebook page", {**result, "facebook_cache_key": cache_key}
            )
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
    def _set_facebook_discovery_request(
        page_id,
        access_token,
        before: Optional[str] = None,
        after: Optional[str] = None,
        fields: Optional[
            str
        ] = "id,name,followers_count,fan_count,about,link,username,verification_status,description,engagement,location,bio,website,company_overview,picture{url}",
    ):
        base_url = (
            f"https://graph.facebook.com/{settings.FACEBOOK_API_VERSION}/{page_id}"
        )
        params = {
            "fields": fields,
            "access_token": access_token,
            "limit": 25,
        }

        if before:
            params["before"] = before
        elif after:
            params["after"] = after

        full_params = f"{base_url}?{urlencode(params)}"
        return base_url, params, full_params

    @staticmethod
    def batch_requests(data: List[MetaBatchRequestData], access_token: str):
        base_url = f"https://graph.facebook.com/{settings.FACEBOOK_API_VERSION}"

        batch_data = []
        for req in data:
            batch_data.append(
                f"%7B'method':'{req['method']}','relative_url':'{req['relative_url']}'%7D"
            )

        full_url = f"{base_url}?batch=[{','.join([str(element) for element in batch_data])}]&include_headers=false&access_token={access_token}"

        print(full_url)

        response = requests.post(full_url)

        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code, detail=response.json()
            )

        return response.json()

    @staticmethod
    async def fetch_facebook_insights(
        entity_id: str,
        metrics: str,
        metric_type: Optional[str] = None,
        period: Optional[str] = "day",
        access_token: Optional[str] = None,
        since: Optional[str | datetime] = None,
        until: Optional[str | datetime] = None,
        previous: Optional[str] = None,
        next: Optional[str] = None,
    ):
        print(f"🔍 [FacebookInsights] Fetching insights for entity_id: {entity_id}")
        print(f"📊 [FacebookInsights] Metrics requested: {metrics}")
        print(f"⏱️  [FacebookInsights] Period: {period}")
        print(f"🔑 [FacebookInsights] Access token (first 20 chars): {access_token[:20] if access_token else 'None'}...")

        if not access_token:
            access_token = settings.META_SYSTEM_TOKEN

        base_url = f"https://graph.facebook.com/{settings.FACEBOOK_API_VERSION}/{entity_id}/insights"

        params: Dict[str, Any] = {"metric": metrics, "period": period}

        if metric_type:
            params["metric_type"] = metric_type
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        if previous:
            params["previous"] = previous
        if next:
            params["next"] = next

        # Encode the parameters, but exclude the access_token
        query_string = urlencode(params)

        # Manually append the access_token at the end
        full_url = f"{base_url}?{query_string}&access_token={access_token}"

        print(f"🌐 [FacebookInsights] Calling Facebook Graph API: {base_url}?{query_string}&access_token=***")

        response = requests.get(full_url)

        print(f"📡 [FacebookInsights] Response status: {response.status_code}")

        if response.status_code != HTTPStatus.OK:
            error_data = response.json()
            print(f"❌ [FacebookInsights] Facebook API Error:")
            print(f"   Status: {response.status_code}")
            print(f"   Error: {error_data}")
            return UriResponse.get_single_data_response(
                "insights",
                None,
                error_data.get("error", {}).get("message", ""),
                code=response.status_code,
            )

        result = response.json()
        print(f"✅ [FacebookInsights] Successfully fetched insights data")

        return UriResponse.get_single_data_response("insights", result)

    @staticmethod
    async def search_facebook_pages(
        access_token: str, name: str, fields: Optional[str] = "id,name,location,link"
    ):
        base_url = (
            f"https://graph.facebook.com/{settings.FACEBOOK_API_VERSION}/pages/search"
        )

        full_url = f"{base_url}?q={name}&fields={fields}&access_token={access_token or settings.META_SYSTEM_TOKEN}"

        response = requests.get(full_url)

        if response.status_code != HTTPStatus.OK:
            return UriResponse.get_single_data_response(
                "pages",
                None,
                response.json()["error"]["message"],
                code=response.status_code,
            )

        result = response.json()

        return UriResponse.get_list_data_response("pages", result["data"])

    @staticmethod
    async def fetch_facebook_page_posts(
        access_token: Optional[str] = None,
        previous: Optional[str] = None,
        next: Optional[str] = None,
    ):
        # Properly encode the `fields` parameter
        fields = (
            "feed{id,created_time,attachments{media,media_type,title,url,description},"
            "comments.limit(50){message,from,created_time},shares,reactions.summary(true)}"
        )
        encoded_fields = urlencode({"fields": fields})

        base_url = f"https://graph.facebook.com/{settings.FACEBOOK_API_VERSION}/me"
        params = {}

        if previous:
            params["previous"] = previous
        if next:
            params["next"] = next
        query_string = urlencode(params)

        # Construct the URL
        full_url = (
            f"{base_url}?{encoded_fields}&{query_string}&access_token={access_token}"
        )

        response = requests.get(full_url)

        result = response.json()

        if response.status_code != HTTPStatus.OK:
            print(response.json())
            return {
                "error": response.json()
                .get("error", {})
                .get("message", "An error occurred"),
                "status": response.status_code,
            }

        return UriResponse.get_single_data_response("posts", result)

    @staticmethod
    async def fetch_facebook_page_stories(
        page_id: str,
        access_token: str,
        previous: Optional[str] = None,
        next: Optional[str] = None,
    ):
        """
        Fetch stories of a Facebook Page.

        **Parameters**:
        - `page_id`: The ID of the Facebook Page.
        - `access_token`: Facebook Page access token.
        - `previous`: Optional pagination token for the previous page.
        - `next`: Optional pagination token for the next page.

        **Returns**:
        - Stories data or an error response.
        """
        # Define the fields to fetch for stories
        fields = "post_id,status,creation_time,media_type,media_id,url"
        encoded_fields = urlencode({"fields": fields})

        base_url = f"https://graph.facebook.com/{settings.FACEBOOK_API_VERSION}/{page_id}/stories"
        params = {"access_token": access_token}

        # Add pagination parameters if provided
        if previous:
            params["previous"] = previous
        if next:
            params["next"] = next

        # Construct the URL
        full_url = f"{base_url}?{encoded_fields}&{urlencode(params)}"

        print("STORIES URL : ", full_url)

        # Make the API request
        response = requests.get(full_url)

        # Handle the API response
        if response.status_code != HTTPStatus.OK:
            return {
                "error": response.json()
                .get("error", {})
                .get("message", "An error occurred"),
                "status": response.status_code,
            }

        print("STORIES RESPONSE : ", response)

        return UriResponse.get_single_data_response("stories", response.json())

    @staticmethod
    async def fetch_facebook_page_reels(
        page_id: str,
        access_token: str,
        previous: Optional[str] = None,
        next: Optional[str] = None,
    ):
        """
        Fetch detailed reels information for a Facebook Page.

        **Parameters**:
        - `page_id`: The ID of the Facebook Page.
        - `access_token`: Facebook Page access token.
        - `previous`: Optional pagination token for the previous page.
        - `next`: Optional pagination token for the next page.

        **Returns**:
        - Detailed reels data or an error response.
        """
        # Define the fields to fetch for reels
        fields = (
            "id,created_time,title,description,source,attachment"
            "thumbnails{uri},length,comments"
            "insights.metric(comment_count,like_count,share_count,total_video_views),"
            "from,total_video_impressions_unique,total_video_impressions,total_video_reactions_by_type_total,post_video_views,post_video_avg_time_watched,post_video_complete_views_30s,post_video_views_unique"
        )
        encoded_fields = urlencode({"fields": fields})

        base_url = f"https://graph.facebook.com/{settings.FACEBOOK_API_VERSION}/{page_id}/video_reels"
        params = {"access_token": access_token}

        if previous:
            params["previous"] = previous
        if next:
            params["next"] = next

        # Construct the URL
        full_url = f"{base_url}?{encoded_fields}&{urlencode(params)}"

        # Make the API request
        response = requests.get(full_url)

        # Handle the API response
        if response.status_code != HTTPStatus.OK:
            return {
                "status": False,
                "responseCode": response.status_code,
                "responseMessage": response.json()
                .get("error", {})
                .get("message", "An error occurred"),
            }

        return UriResponse.get_single_data_response("reels", response.json())

    @staticmethod
    async def fetch_facebook_mentions(
        page_id: str,
        access_token: str,
        previous: Optional[str] = None,
        next: Optional[str] = None,
    ):
        """
        Fetch mentions of a Facebook Page using the Page token.

        **Parameters**:
        - `page_id`: The ID of the Facebook Page.
        - `access_token`: Facebook Page access token.
        - `previous`: Optional pagination token for the previous page.
        - `next`: Optional pagination token for the next page.

        **Returns**:
        - Mentions data or an error response.
        """
        # Properly encode the `fields` parameter to include the desired data
        fields = "id,from,message,created_time,story"

        encoded_fields = urlencode({"fields": fields})

        base_url = (
            f"https://graph.facebook.com/{settings.FACEBOOK_API_VERSION}/{page_id}"
        )
        params = {"access_token": access_token}

        # Add pagination parameters if provided
        if previous:
            params["previous"] = previous
        if next:
            params["next"] = next

        # Construct the URL
        full_url = f"{base_url}/tagged?{encoded_fields}&{urlencode(params)}"

        # Make the API request
        response = requests.get(full_url)

        # Handle the API response
        if response.status_code != HTTPStatus.OK:
            return {
                "error": response.json()
                .get("error", {})
                .get("message", "An error occurred"),
                "status": response.status_code,
            }

        return UriResponse.get_single_data_response("mentions", response.json())

    # @staticmethod
    # def fetch_facebook_mentions(
    #     access_token: Optional[str] = None,
    #     previous: Optional[str] = None,
    #     next: Optional[str] = None,
    # ):
    #     """
    #     Fetch mentions of a Facebook Page.

    #     **Parameters**:
    #     - `access_token`: Facebook Page access token.
    #     - `previous`: Optional pagination token for the previous page.
    #     - `next`: Optional pagination token for the next page.

    #     **Returns**:
    #     - Mentions data or an error response.
    #     """
    #     # Properly encode the `fields` parameter to include the desired data
    #     fields = (
    #         "tagged{id,from,message,created_time,attachments{media,media_type,title,url}}"
    #     )
    #     encoded_fields = urlencode({"fields": fields})

    #     base_url = f"https://graph.facebook.com/{settings.FACEBOOK_API_VERSION}/me"
    #     params = {}

    #     if previous:
    #         params["previous"] = previous
    #     if next:
    #         params["next"] = next
    #     query_string = urlencode(params)

    #     # Construct the URL
    #     full_url = (
    #         f"{base_url}/{encoded_fields}&{query_string}&access_token={access_token}"
    #     )

    #     response = requests.get(full_url)

    #     # Handle response
    #     if response.status_code != HTTPStatus.OK:
    #         return {
    #             "error": response.json()
    #             .get("error", {})
    #             .get("message", "An error occurred"),
    #             "status": response.status_code,
    #         }

    #     return UriResponse.get_single_data_response("mentions", response.json())

    @staticmethod
    async def fetch_facebook_tags(
        page_id: str,
        access_token: str,
        fields: str = "id,message,from,created_time,attachments,likes.summary(true),comments.summary(true),shares",
        since: Optional[str] = None,
        until: Optional[str] = None,
        limit: Optional[int] = 25,
    ):
        """
        Fetch mentions for a Facebook Page.

        **Parameters**:
        - `page_id`: The ID of the Facebook Page.
        - `access_token`: Facebook Page access token.
        - `fields`: Fields to retrieve (default includes id, message, media, comments, likes, etc.).
        - `since`: Start time for fetching mentions (ISO format or UNIX timestamp).
        - `until`: End time for fetching mentions (ISO format or UNIX timestamp).
        - `limit`: Number of mentions per page.

        **Returns**:
        - Mentions data or an error response.
        """
        base_url = f"https://graph.facebook.com/{settings.FACEBOOK_API_VERSION}/{page_id}/tagged"

        # Prepare query parameters
        params = {
            "fields": fields,
            "limit": limit,
            "access_token": access_token,
        }
        if since:
            params["since"] = since
        if until:
            params["until"] = until

        all_data = []
        next_page = None

        while True:
            # Use next page URL if available
            url = base_url if not next_page else next_page
            response = requests.get(url, params=params if not next_page else {})

            if response.status_code != HTTPStatus.OK:
                error_message = (
                    response.json().get("error", {}).get("message", "Unknown error")
                )
                return UriResponse.get_single_data_response(
                    "tags",
                    None,
                    error_message,
                    code=response.status_code,
                )

            result = response.json()
            all_data.extend(result.get("data", []))
            next_page = result.get("paging", {}).get("next")
            if not next_page:
                break

        return UriResponse.get_single_data_response("tags", {"data": all_data})

    @staticmethod
    async def fetch_facebook_page_insights(
        page_id: str,
        metrics: Optional[str],
        period: Optional[str] = "day",
        since: Optional[str] = None,
        until: Optional[str] = None,
        access_token: Optional[str] = None,
    ):
        """
        Fetch insights for a Facebook Page.

        **Parameters**:
        - `page_id`: The ID of the Facebook Page.
        - `metrics`: The metrics to retrieve (comma-separated).
        - `period`: The period for the metrics (e.g., 'day', 'week', 'lifetime'). Default is 'day'.
        - `since`: The start date (UNIX timestamp or ISO format).
        - `until`: The end date (UNIX timestamp or ISO format).
        - `access_token`: Facebook Page access token.

        **Returns**:
        - Insights data or an error response.
        """
        base_url = f"https://graph.facebook.com/{settings.FACEBOOK_API_VERSION}/{page_id}/insights"
        params = {"metric": metrics, "period": period}

        if since:
            params["since"] = since
        if until:
            params["until"] = until

        query_string = urlencode(params)
        full_url = f"{base_url}?{query_string}&access_token={access_token}"

        # Generate a cache key based on the URL
        cache_key = CacheHelper.generate_cache_key(full_url)
        cached_data = await CacheRepository.get_cache(db=None, cache_key=cache_key)
        if cached_data:
            return UriResponse.get_single_data_response("page insights", cached_data)

        response = requests.get(full_url)

        if response.status_code != HTTPStatus.OK:
            return UriResponse.get_single_data_response(
                "page insights", None, response.json().get("error", {}).get("message")
            )

        result = response.json()
        # CacheRepository.set_cache(None, cache_key, result, ttl=FacebookService.CACHE_TTL)

        return UriResponse.get_single_data_response("page insights", result)

    @staticmethod
    async def fetch_facebook_post_insights(
        post_id: str,
        metrics: Optional[str],
        period: Optional[str] = "lifetime",
        access_token: Optional[str] = None,
    ):
        """
        Fetch insights for a specific Facebook post.

        **Parameters**:
        - `post_id`: The ID of the Facebook post.
        - `metrics`: The metrics to retrieve (comma-separated).
        - `period`: The period for the metrics (default: 'lifetime').
        - `access_token`: Facebook Page access token.

        **Returns**:
        - Insights data or an error response.
        """
        if not access_token:
            raise HTTPException(status_code=400, detail="Access token is required.")

        url = (
            f"https://graph.facebook.com/{settings.FACEBOOK_API_VERSION}/{post_id}/insights"
            f"?metric={metrics}&period={period}&access_token={access_token}"
        )

        response = requests.get(url)

        if response.status_code != HTTPStatus.OK:
            return UriResponse.get_single_data_response(
                "post insights", None, response.json().get("error", {}).get("message")
            )

        print("Insights Response : ", response.json())

        return UriResponse.get_single_data_response("post insights", response.json())

    @staticmethod
    async def fetch_videos_insight(
        video_id: str,
        access_token: str,
        metrics: Optional[str] = None,
        period: Optional[str] = "lifetime",
    ):
        """
        Fetch insights for a specific Facebook Reel.

        **Parameters**:
        - `video_id`: The ID of the Reel.
        - `access_token`: Facebook Page access token.
        - `metrics`: Optional, comma-separated metrics to retrieve (default: common reel insights).
        - `period`: The period for the metrics (default: 'lifetime').

        **Returns**:
        - Insights data or an error response.
        """
        # Default metrics for Reels if none are specified
        default_metrics = (
            "blue_reels_play_count,fb_reels_replay_count,fb_reels_total_plays,"
            "post_impressions_unique,post_video_avg_time_watched,post_video_followers,post_video_likes_by_reaction_type,post_video_retention_graph,post_video_social_actions,post_video_view_time"
        )
        metrics = metrics or default_metrics

        # Construct the URL for the insights endpoint
        url = f"https://graph.facebook.com/{settings.FACEBOOK_API_VERSION}/{video_id}/video_insights"
        params = {
            "metric": metrics,
            "period": period,
            "access_token": access_token,
        }

        response = requests.get(f"{url}?{urlencode(params)}")

        # Handle the API response
        if response.status_code != HTTPStatus.OK:
            return {
                "error": response.json()
                .get("error", {})
                .get("message", "An error occurred"),
                "status": response.status_code,
            }

        return UriResponse.get_single_data_response("video insights", response.json())

    @staticmethod
    async def fetch_demographic_insights(
        page_id: str,
        metrics: Optional[str],
        access_token: Optional[str],
    ):
        """
        Fetch demographic insights for a Facebook Page.

        **Parameters**:
        - `page_id`: The ID of the Facebook Page.
        - `metrics`: The metrics to retrieve (e.g., 'page_fans_country').
        - `breakdowns`: The breakdowns for demographics (e.g., 'age,gender').
        - `access_token`: Facebook Page access token.

        **Returns**:
        - Demographic data or an error response.
        """
        url = (
            f"https://graph.facebook.com/{settings.FACEBOOK_API_VERSION}/{page_id}/insights"
            f"?metric={metrics}&access_token={access_token}"
        )

        response = requests.get(url)

        if response.status_code != HTTPStatus.OK:
            return UriResponse.get_single_data_response(
                "demographic insights",
                None,
                response.json().get("error", {}).get("message"),
            )

        return UriResponse.get_single_data_response(
            "demographic insights", response.json()
        )

    @staticmethod
    async def generate_ai_report(data: dict[str, Any], prompt_template: str):
        """
        Generate an AI-driven report for Facebook insights data.

        **Parameters**:
        - `data`: The raw insights data.
        - `prompt_template`: The AI prompt template.

        **Returns**:
        - An AI-generated summary or error response.
        """
        try:
            prompt = prompt_template.format(insights_data=json.dumps(data, indent=2))
            ai_request = chat_model.ChatModel(
                {
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                }
            )

            ai_response = await AIService.chat_completion(ai_request)
            ai_report = json.loads(ai_response.choices[0].message.content.strip())
            return UriResponse.get_single_data_response("ai report", ai_report)

        except (json.JSONDecodeError, KeyError, AttributeError) as e:
            return UriResponse.get_single_data_response(
                "ai report", None, message=f"Failed to parse AI response: {str(e)}"
            )

    @staticmethod
    async def post_on_facebook(page_id: str, post_data: dict, access_token: str):
        """
        Posts content on Facebook, including media uploads.
        """

        print("Page Id :", page_id, "Post Data : ", post_data)
        try:
            # Check and upload media if present
            media_payload = FacebookMultipleMediaPayload(attached_media=[])
            if "media" in post_data and isinstance(post_data.get("media", {}), list):
                for media in post_data.get("media", {}):
                    media_type = media.get("media_type", "").upper()
                    if media_type in ["IMAGE", "VIDEO"]:
                        if media_payload.attached_media is None:
                            media_payload.attached_media = []
                        media_payload.attached_media.append(
                            FacebookPhotoPayload(
                                url=media["url"],
                                caption=media.get("caption", ""),
                                alt_text=media.get("alt_text", ""),
                                media_type=media_type,
                            ).dict()
                            if media_type == "IMAGE"
                            else FacebookVideoPayload(
                                video_url=media["url"],
                                title=media.get("caption", ""),
                                description=media.get("alt_text", ""),
                                file_data=FacebookUploadFile(
                                    file_name="video.mp4",  # Replace with logic if needed
                                    file_length=0,
                                    file_type="video/mp4",
                                ),
                                media_type=media_type,
                            ).dict()
                        )

            # Upload media and attach their IDs to the payload
            if media_payload.attached_media:
                media_payload = await FacebookService.upload_multiple_media(
                    page_id=page_id, payload=media_payload, access_token=access_token
                )

            print("Starting Post Construct : ", media_payload)

            # Construct the post payload
            payload = FacebookHelper.construct_post_payload_from_dict(
                post_data, media_payload
            )
            print("Construct Done...")

            print("Starting Post Publish : ", payload)
            # Publish the post with attached media
            response = await FacebookService.publish_post(
                page_id=page_id, payload=payload, access_token=access_token
            )
            print("Facebook response:", response)
            return response
        except Exception as e:
            print("Error posting to Facebook:", e)
            raise

    # @staticmethod
    # def post_on_facebook(db: Collection, post_data: dict, access_token: str):
    #     page_id = InfluencerRepository.get_influencers_by_filter(
    #         db, user_id=post_data["user_id"], platforms=["FACEBOOK"]
    #     )
    #     page_id = page_id["responseData"]["data"][0]["social_user_id"]

    #     try:
    #         # Check and upload media if present
    #         media_payload = FacebookMultipleMediaPayload(attached_media=[])
    #         if "media" in post_data and isinstance(post_data["media"], list):
    #             for media in post_data["media"]:
    #                 media_type = media.get("media_type", "").upper()
    #                 if media_type in ["IMAGE", "VIDEO"]:
    #                     media_payload.attached_media.append(
    #                         FacebookPhotoPayload(
    #                             url=media["url"],
    #                             caption=media.get("caption", ""),
    #                             alt_text=media.get("alt_text", ""),
    #                             media_type=media_type,
    #                         ).dict()
    #                         if media_type == "IMAGE"
    #                         else FacebookVideoPayload(
    #                             video_url=media["url"],
    #                             title=media.get("caption", ""),
    #                             description=media.get("alt_text", ""),
    #                         ).dict()
    #                     )

    #         # Upload media and attach their IDs to the payload
    #         if media_payload.attached_media:
    #             media_payload = FacebookService.upload_multiple_media(
    #                 page_id=page_id, payload=media_payload, access_token=access_token
    #             )

    #         # Construct the post payload
    #         payload = FacebookHelper.construct_post_payload_from_dict(post_data)

    #         # Attach media IDs to the payload
    #         if media_payload and media_payload.attached_media:
    #             payload.attached_media = media_payload.attached_media

    #         # Convert to dictionary for publishing
    #         payload_dict = payload.dict()

    #         # Publish the post with attached media
    #         response = FacebookService.publish_post(
    #             page_id=page_id, payload=payload_dict, access_token=access_token
    #         )
    #         print("Facebook response:", response)
    #         return response
    #     except Exception as e:
    #         print("Error posting to Facebook:", e)
    #         raise

    @staticmethod
    async def publish_post(
        page_id: str,
        payload: FacebookPostPayload | FacebookMultipleMediaPayload,
        access_token: str,
    ):
        """
        Publishes a post to a Facebook Page.

        :param page_id: The ID of the Facebook Page.
        :param payload: Pydantic model with post data.
        :param access_token: Access token with required permissions.
        """

        url = (
            f"https://graph.facebook.com/{settings.FACEBOOK_API_VERSION}/{page_id}/feed"
        )
        headers = {"Authorization": f"Bearer {access_token}"}

        # Remove `scheduled_publish_time` if the post is not scheduled
        if payload.get("published"):
            payload.pop("scheduled_publish_time", None)

        print("\nPayload dict: ", payload)
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code != HTTPStatus.OK:
            print("Response: ", response.json())
            return UriResponse.get_single_data_response(
                "publish_post", None, code=response.status_code
            )

        return UriResponse.create_response("publish_post", response.json())

    @staticmethod
    async def update_post(
        page_post_id: str, payload: FacebookUpdatePostPayload, access_token: str
    ):
        """
        Updates an existing post on a Facebook Page.

        :param page_post_id: The ID of the post to update.
        :param payload: Pydantic model with updated post data.
        :param access_token: Access token with required permissions.
        """
        url = (
            f"https://graph.facebook.com/{settings.FACEBOOK_API_VERSION}/{page_post_id}"
        )
        headers = {"Authorization": f"Bearer {access_token}"}

        response = requests.post(url, headers=headers, json=payload.dict())
        if response.status_code != HTTPStatus.OK:
            return UriResponse.update_response("update_post", response.json())

        return UriResponse.get_single_data_response("update_post", response.json())

    @staticmethod
    def upload_photo(page_id: str, payload: FacebookPhotoPayload, access_token: str):
        """
        Uploads a photo to a Facebook Page.

        :param page_id: The ID of the Facebook Page.
        :param payload: Pydantic model with photo data.
        :param access_token: Access token with required permissions.
        """
        url = f"https://graph.facebook.com/{settings.FACEBOOK_API_VERSION}/{page_id}/photos"
        headers = {"Authorization": f"Bearer {access_token}"}

        print("Upload Started !!!", payload)
        response = requests.post(url, headers=headers, json=payload.dict())
        print("Upload Done !!!", response.json())
        print("\nResponse for posting image with facebook: ", response.json())
        if response.status_code != HTTPStatus.OK:
            return UriResponse.create_response("upload_photo", response.json())
        return UriResponse.create_response("upload_photo", response.json())

    @staticmethod
    def __start_file_upload_session(file_data: FacebookUploadFile, access_token: str):
        """
        Starts a file upload session

        :param page_id: The ID of the Facebook Page.
        :param file_data: Pydantic model with file data.
        :param access_token: Access token with required permissions
        """
        url = f"https://graph.facebook.com/{settings.FACEBOOK_API_VERSION}/{settings.META_APP_ID}/uploads"
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.post(url, headers=headers, json=file_data.dict())
        if response.status_code == HTTPStatus.OK:
            return response.json()

    @staticmethod
    async def __start_file_upload(
        upload_session_id: str, file_url: str, access_token: str
    ):
        """
        Start file upload

        :param upload_session_id: The ID of the upload session.
        :param file_url: Path to file.
        :param access_token: Access token with required permissions
        """
        url = f"https://graph.facebook.com/{settings.FACEBOOK_API_VERSION}/{upload_session_id}"
        headers = {"Authorization": f"OAuth {access_token}", "file_offset": "0"}
        try:
            with open(file_url, "rb") as file:
                response = requests.post(url, headers=headers, data=file)
        except FileNotFoundError:
            data = await FileHelper.download_file_as_binary(file_url)
            response = requests.post(url, headers=headers, data=data)
        except Exception as e:
            print("Error uploading linkedin image or video: ", e)
            return None
        return response.json()

    @staticmethod
    async def resumable_video_upload(
        page_id: str, payload: FacebookVideoPayload, access_token: str
    ):
        """
        Uploads a video to a Facebook Page.

        :param page_id: The ID of the Facebook Page.
        :param payload: Pydantic model with video data.
        :param access_token: Access token with required permissions.
        """
        url = f"https://graph.facebook.com/{settings.FACEBOOK_API_VERSION}/{page_id}/videos"
        headers = {"Authorization": f"Bearer {access_token}"}

        upload_session_response = FacebookService.__start_file_upload_session(
            payload.file_data, access_token
        )
        if not upload_session_response:
            return UriResponse.error_response("Error starting upload session.")
        print("\nUpload session response: ", upload_session_response)
        upload_session_id = upload_session_response.get("id", None)

        start_file_upload_response = await FacebookService.__start_file_upload(
            upload_session_id=upload_session_id,
            file_url=payload.video_url,
            access_token=access_token,
        )

        if not start_file_upload_response:
            return UriResponse.error_response("Error uploading file.")
        print("\nStart file upload response: ", start_file_upload_response)
        upload_handle = start_file_upload_response.get("h", None)
        payload.video_url = upload_handle
        video_upload_payload = payload.dict()
        del video_upload_payload["file_data"]
        response = requests.post(url, headers=headers, json=video_upload_payload)
        print("\nResponse from uploading video: ", response.json())
        if response.status_code != HTTPStatus.OK:
            return UriResponse.get_single_data_response(
                "upload_video", None, code=response.status_code
            )

        return UriResponse.get_single_data_response("upload_video", response.json())

    @staticmethod
    async def simple_video_upload(
        page_id: str, payload: FacebookVideoPayload, access_token: str
    ):
        """
        Uploads a video to a Facebook Page.

        :param page_id: The ID of the Facebook Page.
        :param payload: Pydantic model with video data.
        :param access_token: Access token with required permissions.
        """
        url = f"https://graph.facebook.com/{settings.FACEBOOK_API_VERSION}/{page_id}/videos"
        headers = {"Authorization": f"Bearer {access_token}"}
        data = payload.dict()
        file_data = {
            "file": (
                payload.file_data.file_name,
                await FileHelper.download_file_as_binary(data["video_url"]),
                payload.file_data.file_type,
            )
        }
        del data["file_data"]
        del data["video_url"]
        response = requests.post(url, headers=headers, data=data, files=file_data)
        print("\nResponse from facebook non resumable video upload: ", response.json())
        if response.status_code != HTTPStatus.OK:
            return UriResponse.create_response("upload_video", None)

        return UriResponse.create_response("upload_video", response.json())

    @staticmethod
    async def upload_multiple_media(
        page_id: str, payload: FacebookMultipleMediaPayload, access_token: str
    ):
        """
        Uploads multiple media items (photos or videos) to a Facebook Page using the Graph API.
        """
        print("Multiple Media Payload : ", payload)
        try:
            if not payload.attached_media or len(payload.attached_media) < 1:
                raise ValueError("Payload must contain a list of attached media.")

            media_fbid_list = []

            print("starting check : ", payload.attached_media)
            if payload.attached_media is not None:
                for media_item in payload.attached_media:
                    print("check done : ", payload.attached_media)
                    media_type = media_item.get("media_type", "")
                    media_item["published"] = False  # Ensure unpublished upload

                    if media_type == "IMAGE":
                        photo_data = FacebookPhotoPayload(**media_item)
                        print("starting image upload....", photo_data)
                        response = FacebookService.upload_photo(
                            page_id=page_id,
                            payload=photo_data,
                            access_token=access_token,
                        )
                        media_id = FacebookService.get_media_id(response)
                        print("complete image upload....", response)
                    elif media_type == "VIDEO":
                        video_data = FacebookVideoPayload(**media_item)
                        print("starting video upload....", video_data)
                        response = FacebookService.simple_video_upload(
                            page_id=page_id,
                            payload=video_data,
                            access_token=access_token,
                        )
                        media_id = FacebookService.get_media_id(response)
                        print("complete video upload....", response)
                    else:
                        raise ValueError(f"Unsupported media type: {media_type}")

                    if media_id is not None:
                        media_fbid_list.append({"media_fbid": media_id})

                    print("Media Facebook ID List : ", media_fbid_list)
                payload.attached_media = media_fbid_list
                print("Final Payload Media IDs:", payload.attached_media)
                return payload
            return {}

        except Exception as e:
            print("Error uploading multiple media:", e)
            raise

    @staticmethod
    async def fetch_ai_post_report(db: AsyncIOMotorDatabase, cache_key: str) -> dict:
        media_report_cache_key = "facebook-ai-post-media-report-" + cache_key

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

        posts = cached_post_data.get("post_data", [])

        MAX_POSTS = 25

        try:
            if len(posts) > 0:
                final_response = await AIPostAnalysisService.generate_ai_post_report(
                    posts[:MAX_POSTS]
                )  # ---- Call to AI
                print("POSTS: ", posts)
                final_response["hashtag_mention_frequency"] = (
                    TextHelper.compute_hashtag_frequency(posts, "content")
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
    async def fetch_ai_post_report_v1(db: AsyncIOMotorDatabase, cache_key: str) -> dict:
        media_report_cache_key = "facebook-ai-post-media-report-" + cache_key

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

        posts_data = await FacebookHelper.extract_data_for_ai_post_insights(
            cached_post_data
        )

        print("Parsed Posts : ", posts_data)
        prompt = ai_prompt.AIChiefAnalystPrompt.FACEBOOK_POST_INSIGHTS_SUMMARY_REQUEST.value.format(
            posts=posts_data
        )
        model = AIService.build_ai_model(
            messages=[{"role": "user", "content": prompt}],
        )

        ai_report = (
            await AIService.structured_chat_completion(model, chat_model.InsightSummary)
        ).dict()

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
    def get_media_id(response: dict) -> str | None:
        if response and response.get("status") is True:
            response_data = response.get("responseData", {})
            media_id = response_data.get("id")
            return media_id
        return None

    # REEL POSTING

    @staticmethod
    def __initialze_reel_upload_session(
        page_id: str, page_access_token: str
    ) -> Optional[dict]:
        url = f"https://graph.facebook.com/{settings.FACEBOOK_API_VERSION}/{page_id}/video_reels"

        headers = {"Content-Type": "application/json"}

        data = {"upload_phase": "start", "access_token": page_access_token}

        response = requests.post(url, json=data, headers=headers)

        response_data = response.json()
        response_code = response.status_code
        print("\nResponse code from initializing reel upload session: ", response_code)
        print("\nResponse data from initializing reel upload session: ", response_data)

        if response_code != HTTPStatus.OK:
            return None
        return response_data

    @staticmethod
    async def __upload_reel_video(
        upload_url: str, page_access_token: str, file_path: str
    ) -> Optional[dict]:

        try:
            video_data = await FileHelper.download_file_as_binary(file_path)
            editted_video_data = FileHelper.enforce_facebook_reel_requirements(
                video_data
            )
        except Exception as e:
            print("\nError occurred in video processing: ", e)
            return None

        headers = {
            "Authorization": f"OAuth {page_access_token}",
            "offset": "0",
            "file_size": str(len(editted_video_data)),
        }

        response = requests.post(upload_url, headers=headers, data=editted_video_data)
        response_code = response.status_code
        response_data = response.json()

        print("\nResponse code from uploading reel video: ", response_code)
        print("\nResponse data from uploading reel video: ", response_data)

        if response_code != HTTPStatus.OK:
            return None
        return response_data

    @staticmethod
    def __check_reel_video_upload_status(video_id: str, page_access_token: str) -> dict:
        url = f"https://graph.facebook.com/{settings.FACEBOOK_API_VERSION}/{video_id}"

        params = {"fields": "status", "access_token": page_access_token}

        response = requests.get(url, params=params)

        response_code = response.status_code
        response_data = response.json()

        print("\nResponse code from uploading reel video: ", response_code)
        print("\nResponse data from uploading reel video: ", response_data)

        video_upload_status_data = response_data.get("status", None)
        video_upload_status = video_upload_status_data.get("uploading_phase", {}).get(
            "status", None
        )
        result = {
            "status": video_upload_status,
            "message": (
                "Video upload completed successfully"
                if video_upload_status == "complete"
                else "Video upload in progress"
            ),
        }
        bytes_transferred = video_upload_status_data.get("uploading_phase", {}).get(
            "bytes_transferred", None
        )
        upload_status = video_upload_status_data.get("uploading_phase", {}).get(
            "status", None
        )
        print("\nUpload status: ", upload_status)
        if upload_status == "interrupted":
            result["status"] = "interrupted"
            result["bytes_transferred"] = bytes_transferred

        error = video_upload_status_data.get("processing_phase", {}).get("error", None)
        if error:
            result["error"] = error
        return result

    @staticmethod
    def __resume_interrupted_video_upload(
        upload_url: str, bytes_transferred: str, page_access_token: str
    ) -> Optional[dict]:
        headers = {
            "Authorization": f"OAuth {page_access_token}",
            "offset": bytes_transferred,
        }

        response = requests.post(upload_url, headers=headers)
        response_code = response.status_code
        response_data = response.json()

        print("\nResponse code from uploading reel video: ", response_code)
        print("\nResponse data from uploading reel video: ", response_data)

        if response_code != HTTPStatus.OK:
            return None
        return response_data

    @staticmethod
    def __publish_uploaded_reel_video(
        page_id: str, page_access_token: str, video_id: str, description: str
    ) -> Optional[dict]:
        url = f"https://graph.facebook.com/{settings.FACEBOOK_API_VERSION}/{page_id}/video_reels"

        params = {
            "access_token": page_access_token,
            "video_id": video_id,
            "upload_phase": "finish",
            "video_state": "PUBLISHED",
            "description": description,
        }

        response = requests.post(url, params=params)

        response_code = response.status_code
        response_data = response.json()

        print("\nResponse code from uploading reel video: ", response_code)
        print("\nResponse data from uploading reel video: ", response_data)

        if response_code != HTTPStatus.OK:
            return None
        return response_data

    @staticmethod
    async def publish_reel_video(
        page_id: str,
        post_data: dict,
        page_access_token: str,
    ) -> dict:
        # Construct payload data
        payload = FacebookHelper.construct_reel_video_payload(post_data)
        print("\nPost facebook reel payload: ", payload)
        # Initialize upload session
        upload_sesson_error_response = UriResponse.error_response(
            "Error starting reel video upload session"
        )
        upload_session_response = FacebookService.__initialze_reel_upload_session(
            page_id=page_id, page_access_token=page_access_token
        )

        if not upload_session_response:
            return upload_sesson_error_response

        video_id = upload_session_response.get("video_id", None)
        upload_url = upload_session_response.get("upload_url", None)

        if not video_id or not upload_url:
            return upload_sesson_error_response

        # Upload video
        upload_video_response = await FacebookService.__upload_reel_video(
            upload_url=upload_url,
            page_access_token=page_access_token,
            file_path=payload.video_url,
        )

        if not upload_video_response or not upload_video_response.get("success", None):
            return UriResponse.error_response("Error uploading reel video")

        MAX_RETRIES = 2  # Set a maximum number of retries to avoid infinite loops
        RETRY_DELAY = 3  # Wait time between retries in seconds

        retries = 0
        while retries < MAX_RETRIES:
            time.sleep(RETRY_DELAY)

            check_video_upload_status_response = (
                FacebookService.__check_reel_video_upload_status(
                    video_id=video_id, page_access_token=page_access_token
                )
            )

            if not check_video_upload_status_response:
                return UriResponse.error_response(
                    "Error checking reel video upload status"
                )

            video_upload_status = check_video_upload_status_response.get("status", "")

            if video_upload_status == "interrupted":
                bytes_transferred = check_video_upload_status_response.get(
                    "bytes_transferred"
                )
                FacebookService.__resume_interrupted_video_upload(
                    upload_url=upload_url,
                    page_access_token=page_access_token,
                    bytes_transferred=str(bytes_transferred),
                )

            elif video_upload_status == "complete":
                result = FacebookService.__publish_uploaded_reel_video(
                    page_id, page_access_token, video_id, payload.description
                )

                return UriResponse.get_single_data_response("Reel video", data=result)

            retries += 1

        # If we reach here, it means the upload was never completed within MAX_RETRIES
        return UriResponse.error_response("Video upload failed after multiple retries")

    @staticmethod
    async def fetch_cached_facebook_posts(
        db: AsyncIOMotorDatabase, facebook_username: str, user_message: str
    ) -> dict:
        """
        Fetch cached Facebook posts for AI processing.
        """
        influencer = await InfluencerRepository.get_influencer_by_username(
            db, facebook_username
        )

        # ✅ Ensure influencer exists before accessing properties
        if not influencer:
            return UriResponse.get_single_data_response(
                "facebook posts for ai report",
                None,
                code=400,
                message="Influencer not found",
            )

        page_id = influencer.get("social_user_id", "")

        posts = await EmbeddingService.vector_search_account_tracking_data(
            db, page_id, PostPlatformEnum.FACEBOOK.value, user_message
        )

        return UriResponse.get_single_data_response(
            "facebook posts for ai report", posts
        )

        # token = influencer.get("token", "")

        # # ✅ Ensure valid token is available
        # if not token:
        #     return UriResponse.get_single_data_response(
        #         "facebook posts for ai report",
        #         None,
        #         code=400,
        #         message="Missing access token",
        #     )

        # # ✅ Correctly extract values from `_set_facebook_discovery_request`
        # base_url, params, full_params = FacebookService._set_facebook_discovery_request(
        #     page_id, token
        # )

        # cache_key: str = CacheHelper.generate_cache_key(full_params)

        # cached_post_data = await CacheRepository.get_cache(db, cache_key)
        # if not cached_post_data:
        #     return UriResponse.get_single_data_response(
        #         "facebook posts for ai report", None
        #     )

        # # ✅ Extract relevant data for AI post insights
        # posts = await FacebookHelper.extract_data_for_ai_post_insights(cached_post_data)

    @staticmethod
    async def generate_raw_metadata_for_report_gen(
        db: AsyncIOMotorDatabase, report_generation_data: ReportGenerationRequest
    ):
        try:
            if (
                not report_generation_data.influencer_ids
                or not report_generation_data.influencer_ids.facebook
            ):
                raise ValueError(
                    "Influencer ID not provided for facebook account tracking report gen"
                )
            token, social_id, username = (
                await ReportGenerationHelper.get_influencer_data(
                    db,
                    report_generation_data.influencer_ids.facebook,
                    report_generation_data.user_id,
                )
            )
            start_date, end_date, previous_start = (
                ReportGenerationHelper.calculate_date_range(
                    report_generation_data.period
                )
            )
            metrics = "page_post_engagements,page_impressions,page_fans_country,page_daily_follows,page_impressions_unique"
            facebook_insights_params = FacebookInsightsParameters(
                entity_id=social_id,
                metrics=metrics,
                metric_type="total_value",
                access_token=token,
            )

            current_period_insights = await FacebookService.get_insights_for_report_gen(
                facebook_insights_params, start_date, end_date
            )
            previous_period_insights = (
                await FacebookService.get_insights_for_report_gen(
                    facebook_insights_params, previous_start, start_date
                )
            )
            facebook_account_info = await FacebookService.fetch_facebook_page_discovery(
                page_id=social_id, access_token=token, db=db
            )
            if not facebook_account_info.get("status"):
                raise ValueError("Facebook account info not gotten successfully")
            account_info = facebook_account_info.get("responseData")
            if len(account_info.get("post_data", [])) == 0:
                raise ValueError(
                    "No posts to analyze for facebook account tracking report generation."
                )

            metadata = ReportMetadataModel(
                account_info=account_info,
                current_period_insights=current_period_insights,
                previous_period_insights=previous_period_insights,
            ).dict(exclude_none=True)
            return metadata
        except Exception as e:
            print("Error occurred in getting facebook metadata: ", e)
            raise

    @staticmethod
    async def get_insights_for_report_gen(
        params: FacebookInsightsParameters, since, until
    ):
        response = await FacebookService.fetch_facebook_insights(
            **params.dict(exclude_none=True), since=since, until=until
        )
        if not response.get("status"):
            raise ValueError(
                f"Insights data not gotten from Facebook for {since} to {until}"
            )
        return response.get("responseData")
