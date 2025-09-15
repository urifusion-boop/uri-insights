from datetime import timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase

from fastapi import HTTPException
from http import HTTPStatus
from app.repository.CacheRepository import CacheRepository
from app.core.helpers.cache_helper import CacheHelper
from app.domain.responses.uri_response import UriResponse
import requests
from typing import Dict, Any, Optional
from app.domain.requests.twitter_requests import FollowsParams


class XFollowsService:
    BASE_URL = "https://api.x.com/2/users"
    CACHE_TTL = timedelta(minutes=15)  # Cache for 15 minutes

    @staticmethod
    async def get_followers(
        db: AsyncIOMotorDatabase, user_id: str, params: FollowsParams, access_token: str
    ) -> Dict[str, Any]:
        """
        Fetch followers of a specific user.
        :param db: AsyncIOMotorDatabase instance for caching.
        :param user_id: Twitter user ID to fetch followers for.
        :param params: Query parameters for the request.
        :param access_token: Bearer token for authentication.
        :return: JSON response from the API.
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        params_dict = params.dict(exclude_none=True)

        # Generate cache key
        cache_key = CacheHelper.generate_cache_key(
            f"{XFollowsService.BASE_URL}/{user_id}/followers{params_dict}"
        )

        # Check cache
        cached_data = await CacheRepository.get_cache(db, cache_key=cache_key)
        if cached_data:
            return UriResponse.get_single_data_response("followers", cached_data)

        # Make request
        url = f"{XFollowsService.BASE_URL}/{user_id}/followers"
        response = requests.get(url, headers=headers, params=params_dict)

        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("error", "Failed to fetch followers."),
            )

        result = response.json()

        # Cache the response
        await CacheRepository.set_cache(
            db=db, cache_key=cache_key, data=result, ttl=XFollowsService.CACHE_TTL
        )

        return UriResponse.get_single_data_response("followers", result)

    @staticmethod
    async def get_following(
        db: AsyncIOMotorDatabase, user_id: str, params: FollowsParams, access_token: str
    ) -> Dict[str, Any]:
        """
        Fetch users followed by a specific user.
        :param db: AsyncIOMotorDatabase instance for caching.
        :param user_id: Twitter user ID to fetch following for.
        :param params: Query parameters for the request.
        :param access_token: Bearer token for authentication.
        :return: JSON response from the API.
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        params_dict = params.dict(exclude_none=True)

        # Generate cache key
        cache_key = CacheHelper.generate_cache_key(
            f"{XFollowsService.BASE_URL}/{user_id}/following{params_dict}"
        )

        # Check cache
        cached_data = await CacheRepository.get_cache(db, cache_key=cache_key)
        if cached_data:
            return UriResponse.get_single_data_response("following", cached_data)

        # Make request
        url = f"{XFollowsService.BASE_URL}/{user_id}/following"
        response = requests.get(url, headers=headers, params=params_dict)

        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("error", "Failed to fetch following."),
            )

        result = response.json()

        # Cache the response
        await CacheRepository.set_cache(
            db=db, cache_key=cache_key, data=result, ttl=XFollowsService.CACHE_TTL
        )

        return UriResponse.get_single_data_response("following", result)
