from motor.motor_asyncio import AsyncIOMotorDatabase

from fastapi import HTTPException
from http import HTTPStatus
from app.repository.CacheRepository import CacheRepository
from app.core.helpers.cache_helper import CacheHelper
from app.domain.responses.uri_response import UriResponse
import requests
from datetime import timedelta
from typing import Dict, Any
from app.domain.requests.twitter_requests import LikesParams, LikedTweetsParams


class XLikesService:
    BASE_URL = "https://api.x.com/2/tweets/{tweet_id}/liking_users"
    CACHE_TTL = timedelta(minutes=15)  # Cache for 15 minutes

    @staticmethod
    async def get_liking_users(
        db: AsyncIOMotorDatabase, tweet_id: str, params: LikesParams, access_token: str
    ) -> Dict[str, Any]:
        """
        Fetch users who liked a specific Tweet.
        :param db: AsyncIOMotorDatabase instance for caching.
        :param tweet_id: The Tweet ID to fetch liking users for.
        :param params: Pydantic model containing query parameters.
        :param access_token: Bearer token for authentication.
        :return: JSON response from the API.
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        params_dict = params.dict(exclude_none=True)  # Convert Pydantic model to a dict
        url = XLikesService.BASE_URL.format(tweet_id=tweet_id)

        # Generate cache key
        cache_key = CacheHelper.generate_cache_key(f"{url}{params_dict}")

        # Check cache
        cached_data = await CacheRepository.get_cache(db, cache_key=cache_key)
        if cached_data:
            return UriResponse.get_single_data_response("liking_users", cached_data)

        # Make request
        response = requests.get(url, headers=headers, params=params_dict)

        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("error", "Failed to fetch liking users."),
            )

        result = response.json()

        # Cache the response
        await CacheRepository.set_cache(
            db=db, cache_key=cache_key, data=result, ttl=XLikesService.CACHE_TTL
        )

        return UriResponse.get_single_data_response("liking_users", result)

    @staticmethod
    async def get_user_liked_tweets(
        db: AsyncIOMotorDatabase,
        user_id: str,
        params: LikedTweetsParams,
        access_token: str,
    ) -> Dict[str, Any]:
        """
        Fetch Tweets liked by a specific user.
        :param db: AsyncIOMotorDatabase instance for caching.
        :param user_id: The User ID to fetch liked Tweets for.
        :param params: Pydantic model containing query parameters.
        :param access_token: Bearer token for authentication.
        :return: JSON response from the API.
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        params_dict = params.dict(exclude_none=True)  # Convert Pydantic model to a dict
        url = XLikesService.BASE_URL.format(user_id=user_id)

        # Generate cache key
        cache_key = CacheHelper.generate_cache_key(f"{url}{params_dict}")

        # Check cache
        cached_data = await CacheRepository.get_cache(db, cache_key=cache_key)
        if cached_data:
            return UriResponse.get_single_data_response("liked_tweets", cached_data)

        # Make request
        response = requests.get(url, headers=headers, params=params_dict)

        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get(
                    "error", "Failed to fetch user's liked Tweets."
                ),
            )

        result = response.json()

        # Cache the response
        await CacheRepository.set_cache(
            db=db, cache_key=cache_key, data=result, ttl=XLikesService.CACHE_TTL
        )

        return UriResponse.get_single_data_response("liked_tweets", result)
