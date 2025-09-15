from datetime import timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase

from fastapi import HTTPException
from http import HTTPStatus
from app.repository.CacheRepository import CacheRepository
from app.core.helpers.cache_helper import CacheHelper
from app.domain.responses.uri_response import UriResponse
import requests
from typing import Dict, Any
from app.domain.requests.twitter_requests import TweetCountsParams


class XTweetCountService:
    BASE_URL_TWEET_COUNTS = "https://api.x.com/2/tweets/counts/all"
    BASE_URL_TWEET_COUNTS_RECENT = "https://api.x.com/2/tweets/counts/recent"
    CACHE_TTL = timedelta(minutes=15)  # Cache for 15 minutes

    @staticmethod
    async def get_tweet_counts(
        db: AsyncIOMotorDatabase, params: TweetCountsParams, access_token: str
    ) -> Dict[str, Any]:
        """
        Fetch full-archive Tweet counts matching the query.
        :param db: AsyncIOMotorDatabase instance for caching.
        :param params: Pydantic model containing query parameters.
        :param access_token: Bearer token for authentication.
        :return: JSON response from the API.
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        params_dict = params.dict(exclude_none=True)  # Convert Pydantic model to a dict

        # Generate cache key
        cache_key = CacheHelper.generate_cache_key(
            f"{XTweetCountService.BASE_URL_TWEET_COUNTS}{params_dict}"
        )

        # Check cache
        cached_data = await CacheRepository.get_cache(db, cache_key=cache_key)
        if cached_data:
            return UriResponse.get_single_data_response("tweet_counts", cached_data)

        # Make request
        response = requests.get(
            XTweetCountService.BASE_URL_TWEET_COUNTS,
            headers=headers,
            params=params_dict,
        )

        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("error", "Failed to fetch tweet counts."),
            )

        result = response.json()

        # Cache the response
        await CacheRepository.set_cache(
            db=db, cache_key=cache_key, data=result, ttl=XTweetCountService.CACHE_TTL
        )

        return UriResponse.get_single_data_response("tweet_counts", result)

    @staticmethod
    async def get_recent_tweet_counts(
        db: AsyncIOMotorDatabase, params: TweetCountsParams, access_token: str
    ) -> Dict[str, Any]:
        """
        Fetch recent Tweet counts (from the past 7 days) matching the query.
        :param db: AsyncIOMotorDatabase instance for caching.
        :param params: Pydantic model containing query parameters.
        :param access_token: Bearer token for authentication.
        :return: JSON response from the API.
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        params_dict = params.dict(exclude_none=True)  # Convert Pydantic model to a dict

        # Generate cache key
        cache_key = CacheHelper.generate_cache_key(
            f"{XTweetCountService.BASE_URL_TWEET_COUNTS_RECENT}{params_dict}"
        )

        # Check cache
        cached_data = await CacheRepository.get_cache(db, cache_key=cache_key)
        if cached_data:
            return UriResponse.get_single_data_response(
                "tweet_counts_recent", cached_data
            )

        # Make request
        response = requests.get(
            XTweetCountService.BASE_URL_TWEET_COUNTS_RECENT,
            headers=headers,
            params=params_dict,
        )

        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get(
                    "error", "Failed to fetch recent tweet counts."
                ),
            )

        result = response.json()

        # Cache the response
        await CacheRepository.set_cache(
            db=db, cache_key=cache_key, data=result, ttl=XTweetCountService.CACHE_TTL
        )

        return UriResponse.get_single_data_response("tweet_counts_recent", result)
