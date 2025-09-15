from datetime import timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase

from fastapi import HTTPException
from http import HTTPStatus
from app.repository.CacheRepository import CacheRepository
from app.core.helpers.cache_helper import CacheHelper
from app.domain.responses.uri_response import UriResponse
import requests
from typing import Dict, Any, Optional
from app.domain.requests.twitter_requests import TimelineParams, MentionsParams
from app.core.helpers.object_helper import ObjectHelper


class XTimelineService:
    TIMELINE_BASE_URL = "https://api.x.com/2/users/{user_id}/tweets"
    MENTIONS_BASE_URL = "https://api.x.com/2/users/{user_id}/mentions"
    REVERSE_TIMELINE_BASE_URL = (
        "https://api.x.com/2/users/{user_id}/timelines/reverse_chronological"
    )
    CACHE_TTL = timedelta(minutes=15)  # Cache for 15 minutes

    @staticmethod
    def get_user_tweets(
        db: AsyncIOMotorDatabase,
        user_id: str,
        access_token: str,
        params: Optional[TimelineParams],
    ) -> Dict[str, Any]:
        """
        Fetch tweets from a specific user's timeline.
        :param user_id: The user ID for the timeline.
        :param params: Pydantic model containing query parameters.
        :param access_token: Bearer token for authentication.
        :return: JSON response from the API.
        """
        headers = {"Authorization": f"Bearer {access_token}"}

        # Apply the replacements
        transformed_params = ObjectHelper.transform_twitter_fields_params(params)

        # API endpoint
        url = f"https://api.twitter.com/2/users/{user_id}/tweets"

        print("Final API URL:", url)
        print("Parameters sent:", transformed_params)

        # Make the API request
        response = requests.get(url, headers=headers, params=transformed_params)

        if response.status_code != HTTPStatus.OK:
            print("Error Response:", response.json())
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get(
                    "error", "Failed to fetch user timeline tweets."
                ),
            )

        result = response.json()
        print("Response:", result)

        return UriResponse.get_single_data_response("tweets", result)

    @staticmethod
    async def get_user_mentions(
        db: AsyncIOMotorDatabase,
        user_id: str,
        params: MentionsParams,
        access_token: str,
    ) -> Dict[str, Any]:
        """
        Fetch tweets mentioning a specific user.
        :param user_id: The user ID for mentions.
        :param params: Pydantic model containing query parameters.
        :param access_token: Bearer token for authentication.
        :return: JSON response from the API.
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        params_dict = ObjectHelper.transform_twitter_fields_params(params)
        url = XTimelineService.MENTIONS_BASE_URL.format(user_id=user_id)

        # Generate cache key
        cache_key = CacheHelper.generate_cache_key(f"{url}{params_dict}")

        # Check cache
        cached_data = await CacheRepository.get_cache(db, cache_key=cache_key)
        if cached_data:
            return UriResponse.get_single_data_response("mentions", cached_data)

        # Make request
        response = requests.get(url, headers=headers, params=params_dict)

        print("User Mentions : ", response.json())
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("error", "Failed to fetch user mentions."),
            )

        result = response.json()

        # Cache the response
        await CacheRepository.set_cache(
            db=db, cache_key=cache_key, data=result, ttl=XTimelineService.CACHE_TTL
        )

        return UriResponse.get_single_data_response("mentions", result)

    @staticmethod
    async def get_reverse_chronological_timeline(
        db: AsyncIOMotorDatabase,
        user_id: str,
        params: TimelineParams,
        access_token: str,
    ) -> Dict[str, Any]:
        """
        Fetch reverse chronological timeline for a user.
        :param user_id: The user ID requesting their timeline.
        :param params: Pydantic model containing query parameters.
        :param access_token: Bearer token for authentication.
        :return: JSON response from the API.
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        params_dict = ObjectHelper.transform_twitter_fields_params(params)
        url = XTimelineService.REVERSE_TIMELINE_BASE_URL.format(user_id=user_id)

        # Generate cache key
        cache_key = CacheHelper.generate_cache_key(f"{url}{params_dict}")

        # Check cache
        cached_data = await CacheRepository.get_cache(db, cache_key=cache_key)
        if cached_data:
            return UriResponse.get_single_data_response("reverse_timeline", cached_data)

        # Make request
        response = requests.get(url, headers=headers, params=params_dict)

        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get(
                    "error", "Failed to fetch reverse chronological timeline."
                ),
            )

        result = response.json()

        # Cache the response
        await CacheRepository.set_cache(
            db=db, cache_key=cache_key, data=result, ttl=XTimelineService.CACHE_TTL
        )

        return UriResponse.get_single_data_response("reverse_timeline", result)
