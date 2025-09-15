from motor.motor_asyncio import AsyncIOMotorDatabase

from fastapi import HTTPException
from http import HTTPStatus
from datetime import timedelta
from typing import Dict, Any
import requests
from app.repository.CacheRepository import CacheRepository
from app.core.helpers.cache_helper import CacheHelper
from app.domain.responses.uri_response import UriResponse
from app.domain.requests.twitter_requests import (
    RetweetedByParams,
    RetweetsParams,
    CreateRetweetPayload,
)


class XReTweetService:
    """
    Service for managing Retweets via the X API.
    Provides methods to:
    - Fetch users who retweeted a specific tweet
    - Create a retweet on behalf of a user
    - Fetch retweets for a specific tweet
    """

    BASE_URL = "https://api.x.com/2/tweets"
    CACHE_TTL = timedelta(minutes=15)  # Cache for 15 minutes

    @staticmethod
    async def get_retweeted_by(
        db: AsyncIOMotorDatabase,
        tweet_id: str,
        params: RetweetedByParams,
        access_token: str,
    ) -> Dict[str, Any]:
        """
        Fetches information about users who retweeted a specific Tweet.

        :param db: AsyncIOMotorDatabase instance for caching.
        :param tweet_id: Unique identifier of the Tweet.
        :param params: Query parameters for filtering results.
        :param access_token: Bearer token for authentication.
        :return: JSON response containing information about retweeting users.
        """
        headers = {"Authorization": f"Bearer {access_token}"}

        # Generate cache key
        cache_key = CacheHelper.generate_cache_key(
            f"{XReTweetService.BASE_URL}/{tweet_id}/retweeted_by?{params}"
        )

        # Check cache
        cached_data = await CacheRepository.get_cache(db, cache_key=cache_key)
        if cached_data:
            return UriResponse.get_single_data_response("retweeted_by", cached_data)

        # Make API request
        response = requests.get(
            f"{XReTweetService.BASE_URL}/{tweet_id}/retweeted_by",
            headers=headers,
            params=params,
        )
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get(
                    "error", "Failed to retrieve retweeted users."
                ),
            )

        result = response.json()
        # Cache response
        await CacheRepository.set_cache(
            db=db, cache_key=cache_key, data=result, ttl=XReTweetService.CACHE_TTL
        )

        return UriResponse.get_single_data_response("retweeted_by", result)

    @staticmethod
    def create_retweet(
        user_id: str, payload: CreateRetweetPayload, access_token: str
    ) -> Dict[str, Any]:
        """
        Retweets a Tweet on behalf of the authenticated user.

        :param db: AsyncIOMotorDatabase instance for logging or future use.
        :param user_id: Unique identifier of the user retweeting the Tweet.
        :param payload: JSON payload containing the Tweet ID to retweet.
        :param access_token: Bearer token for authentication.
        :return: JSON response indicating the retweet operation's success.
        """
        headers = {"Authorization": f"Bearer {access_token}"}

        # Make API request
        response = requests.post(
            f"{XReTweetService.BASE_URL}/users/{user_id}/retweets",
            headers=headers,
            json=payload,
        )
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("error", "Failed to create retweet."),
            )

        return UriResponse.get_single_data_response("retweeted", response.json())

    @staticmethod
    async def get_retweets(
        db: AsyncIOMotorDatabase,
        tweet_id: str,
        params: RetweetsParams,
        access_token: str,
    ) -> Dict[str, Any]:
        """
        Retrieves retweets for a specific Tweet ID.

        :param db: AsyncIOMotorDatabase instance for caching.
        :param tweet_id: Unique identifier of the Tweet.
        :param params: Query parameters for filtering results.
        :param access_token: Bearer token for authentication.
        :return: JSON response containing information about retweets.
        """
        headers = {"Authorization": f"Bearer {access_token}"}

        # Generate cache key
        cache_key = CacheHelper.generate_cache_key(
            f"{XReTweetService.BASE_URL}/{tweet_id}/retweets?{params}"
        )

        # Check cache
        cached_data = await CacheRepository.get_cache(db, cache_key=cache_key)
        if cached_data:
            return UriResponse.get_single_data_response("retweets", cached_data)

        # Make API request
        response = requests.get(
            f"{XReTweetService.BASE_URL}/{tweet_id}/retweets",
            headers=headers,
            params=params,
        )
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("error", "Failed to retrieve retweets."),
            )

        result = response.json()
        # Cache response
        await CacheRepository.set_cache(
            db=db, cache_key=cache_key, data=result, ttl=XReTweetService.CACHE_TTL
        )

        return UriResponse.get_single_data_response("retweets", result)
