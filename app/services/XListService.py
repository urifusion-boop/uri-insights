from http import HTTPStatus
from typing import Dict, Any
import requests
from app.repository.CacheRepository import CacheRepository
from app.core.helpers.cache_helper import CacheHelper
from app.domain.responses.uri_response import UriResponse
from datetime import timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase

from fastapi import HTTPException
from app.domain.requests.twitter_requests import (
    ListLookupParams,
    ListTweetsParams,
    ListMembersParams,
    PinnedListsParams,
    OwnedListsParams,
)


class XListService:
    """
    Service for managing Twitter Lists via the X API.
    """

    BASE_URL = "https://api.x.com/2"
    CACHE_TTL = timedelta(minutes=15)

    @staticmethod
    async def get_list_by_id(
        db: AsyncIOMotorDatabase,
        list_id: str,
        params: ListLookupParams,
        access_token: str,
    ) -> Dict[str, Any]:
        """
        Fetch details of a specific list.
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        cache_key = CacheHelper.generate_cache_key(
            f"{XListService.BASE_URL}/lists/{list_id}?{params}"
        )

        # Check cache
        cached_data = await CacheRepository.get_cache(db, cache_key=cache_key)
        if cached_data:
            return UriResponse.get_single_data_response("list", cached_data)

        # Make API request
        response = requests.get(
            f"{XListService.BASE_URL}/lists/{list_id}",
            headers=headers,
            params=params.dict(exclude_none=True),
        )
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("error", "Failed to fetch list details."),
            )

        result = response.json()
        await CacheRepository.set_cache(
            db=db, cache_key=cache_key, data=result, ttl=XListService.CACHE_TTL
        )
        return UriResponse.get_single_data_response("list", result)

    @staticmethod
    async def get_owned_lists(
        db: AsyncIOMotorDatabase,
        user_id: str,
        params: OwnedListsParams,
        access_token: str,
    ) -> Dict[str, Any]:
        """
        Fetch lists owned by a user.
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        cache_key = CacheHelper.generate_cache_key(
            f"{XListService.BASE_URL}/users/{user_id}/owned_lists?{params}"
        )

        # Check cache
        cached_data = await CacheRepository.get_cache(db, cache_key=cache_key)
        if cached_data:
            return UriResponse.get_single_data_response("owned_lists", cached_data)

        # Make API request
        response = requests.get(
            f"{XListService.BASE_URL}/users/{user_id}/owned_lists",
            headers=headers,
            params=params.dict(exclude_none=True),
        )
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("error", "Failed to fetch owned lists."),
            )

        result = response.json()
        await CacheRepository.set_cache(
            db=db, cache_key=cache_key, data=result, ttl=XListService.CACHE_TTL
        )
        return UriResponse.get_single_data_response("owned_lists", result)

    @staticmethod
    async def get_list_tweets(
        db: AsyncIOMotorDatabase,
        list_id: str,
        params: ListTweetsParams,
        access_token: str,
    ) -> Dict[str, Any]:
        """
        Fetch tweets from a specific list.
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        cache_key = CacheHelper.generate_cache_key(
            f"{XListService.BASE_URL}/lists/{list_id}/tweets?{params}"
        )

        # Check cache
        cached_data = await CacheRepository.get_cache(db, cache_key=cache_key)
        if cached_data:
            return UriResponse.get_single_data_response("list_tweets", cached_data)

        # Make API request
        response = requests.get(
            f"{XListService.BASE_URL}/lists/{list_id}/tweets",
            headers=headers,
            params=params.dict(exclude_none=True),
        )
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("error", "Failed to fetch list tweets."),
            )

        result = response.json()
        await CacheRepository.set_cache(
            db=db, cache_key=cache_key, data=result, ttl=XListService.CACHE_TTL
        )
        return UriResponse.get_single_data_response("list_tweets", result)

    @staticmethod
    async def get_list_members(
        db: AsyncIOMotorDatabase,
        list_id: str,
        params: ListMembersParams,
        access_token: str,
    ) -> Dict[str, Any]:
        """
        Fetch members of a specific list.
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        cache_key = CacheHelper.generate_cache_key(
            f"{XListService.BASE_URL}/lists/{list_id}/members?{params}"
        )

        # Check cache
        cached_data = await CacheRepository.get_cache(db, cache_key=cache_key)
        if cached_data:
            return UriResponse.get_single_data_response("list_members", cached_data)

        # Make API request
        response = requests.get(
            f"{XListService.BASE_URL}/lists/{list_id}/members",
            headers=headers,
            params=params.dict(exclude_none=True),
        )
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("error", "Failed to fetch list members."),
            )

        result = response.json()
        await CacheRepository.set_cache(
            db=db, cache_key=cache_key, data=result, ttl=XListService.CACHE_TTL
        )
        return UriResponse.get_single_data_response("list_members", result)

    @staticmethod
    async def get_pinned_lists(
        db: AsyncIOMotorDatabase,
        user_id: str,
        params: PinnedListsParams,
        access_token: str,
    ) -> Dict[str, Any]:
        """
        Fetch pinned lists of a specific user.

        :param db: AsyncIOMotorDatabase instance for caching.
        :param user_id: User ID whose pinned lists are being fetched.
        :param params: Query parameters for filtering results.
        :param access_token: Bearer token for authentication.
        :return: JSON response containing pinned lists.
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        cache_key = CacheHelper.generate_cache_key(
            f"{XListService.BASE_URL}/users/{user_id}/pinned_lists?{params}"
        )

        # Check cache
        cached_data = await CacheRepository.get_cache(db, cache_key=cache_key)
        if cached_data:
            return UriResponse.get_single_data_response("pinned_lists", cached_data)

        # Make API request
        response = requests.get(
            f"{XListService.BASE_URL}/users/{user_id}/pinned_lists",
            headers=headers,
            params=params.dict(exclude_none=True),
        )
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("error", "Failed to fetch pinned lists."),
            )

        result = response.json()
        await CacheRepository.set_cache(
            db=db, cache_key=cache_key, data=result, ttl=XListService.CACHE_TTL
        )
        return UriResponse.get_single_data_response("pinned_lists", result)
