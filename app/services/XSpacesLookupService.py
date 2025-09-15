from motor.motor_asyncio import AsyncIOMotorDatabase

from fastapi import HTTPException
from http import HTTPStatus
from app.repository.CacheRepository import CacheRepository
from app.core.helpers.cache_helper import CacheHelper
from app.domain.responses.uri_response import UriResponse
import requests
from datetime import timedelta
from typing import Dict, Any
from app.domain.requests.twitter_requests import (
    SpaceSearchParams,
    SpaceLookupParams,
    CreatorSpacesParams,
    SpaceBuyersParams,
)


class XSpacesLookupService:
    BASE_URL = "https://api.x.com/2/spaces"
    CACHE_TTL = timedelta(minutes=15)  # Cache for 15 minutes

    @staticmethod
    async def search_spaces(
        db: AsyncIOMotorDatabase, params: SpaceSearchParams, access_token: str
    ) -> Dict[str, Any]:
        """
        Search for live or scheduled Spaces by query.
        :param db: AsyncIOMotorDatabase instance for caching.
        :param query: Search term for Spaces.
        :param params: Additional query parameters.
        :param access_token: Bearer token for authentication.
        :return: JSON response from the API.
        """
        headers = {"Authorization": f"Bearer {access_token}"}

        # Generate cache key
        cache_key = CacheHelper.generate_cache_key(
            f"{XSpacesLookupService.BASE_URL}/search?{params}"
        )

        # Check cache
        cached_data = await CacheRepository.get_cache(db, cache_key=cache_key)
        if cached_data:
            return UriResponse.get_single_data_response("spaces", cached_data)

        # Make request
        response = requests.get(
            f"{XSpacesLookupService.BASE_URL}/search", headers=headers, params=params
        )
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("error", "Failed to search Spaces."),
            )

        result = response.json()
        # Cache the response
        await CacheRepository.set_cache(
            db=db, cache_key=cache_key, data=result, ttl=XSpacesLookupService.CACHE_TTL
        )

        return UriResponse.get_single_data_response("spaces", result)

    @staticmethod
    async def lookup_spaces(
        db: AsyncIOMotorDatabase, params: SpaceLookupParams, access_token: str
    ) -> Dict[str, Any]:
        """
        Lookup Spaces by their IDs.
        :param db: AsyncIOMotorDatabase instance for caching.
        :param ids: Comma-separated list of Space IDs.
        :param params: Additional query parameters.
        :param access_token: Bearer token for authentication.
        :return: JSON response from the API.
        """
        headers = {"Authorization": f"Bearer {access_token}"}

        # Generate cache key
        cache_key = CacheHelper.generate_cache_key(
            f"{XSpacesLookupService.BASE_URL}?{params}"
        )

        # Check cache
        cached_data = await CacheRepository.get_cache(db, cache_key=cache_key)
        if cached_data:
            return UriResponse.get_single_data_response("spaces", cached_data)

        # Make request
        response = requests.get(
            f"{XSpacesLookupService.BASE_URL}", headers=headers, params=params
        )
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("error", "Failed to lookup Spaces by IDs."),
            )

        result = response.json()
        # Cache the response
        await CacheRepository.set_cache(
            db=db, cache_key=cache_key, data=result, ttl=XSpacesLookupService.CACHE_TTL
        )

        return UriResponse.get_single_data_response("spaces", result)

    @staticmethod
    async def lookup_spaces_by_creators(
        db: AsyncIOMotorDatabase, params: CreatorSpacesParams, access_token: str
    ) -> Dict[str, Any]:
        """
        Lookup Spaces created by specific user IDs.
        :param db: AsyncIOMotorDatabase instance for caching.
        :param user_ids: Comma-separated list of user IDs.
        :param params: Additional query parameters.
        :param access_token: Bearer token for authentication.
        :return: JSON response from the API.
        """
        headers = {"Authorization": f"Bearer {access_token}"}

        # Generate cache key
        cache_key = CacheHelper.generate_cache_key(
            f"{XSpacesLookupService.BASE_URL}/by/creator_ids?{params}"
        )

        # Check cache
        cached_data = await CacheRepository.get_cache(db, cache_key=cache_key)
        if cached_data:
            return UriResponse.get_single_data_response("spaces", cached_data)

        # Make request
        response = requests.get(
            f"{XSpacesLookupService.BASE_URL}/by/creator_ids",
            headers=headers,
            params=params,
        )
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get(
                    "error", "Failed to lookup Spaces by creator IDs."
                ),
            )

        result = response.json()
        # Cache the response
        await CacheRepository.set_cache(
            db=db, cache_key=cache_key, data=result, ttl=XSpacesLookupService.CACHE_TTL
        )

        return UriResponse.get_single_data_response("spaces", result)

    @staticmethod
    async def get_space_buyers(
        db: AsyncIOMotorDatabase,
        space_id: str,
        params: SpaceBuyersParams,
        access_token: str,
    ) -> Dict[str, Any]:
        """
        Get buyers of a ticketed Space.
        :param db: AsyncIOMotorDatabase instance for caching.
        :param space_id: ID of the Space.
        :param params: Additional query parameters.
        :param access_token: Bearer token for authentication.
        :return: JSON response from the API.
        """
        headers = {"Authorization": f"Bearer {access_token}"}

        # Generate cache key
        cache_key = CacheHelper.generate_cache_key(
            f"{XSpacesLookupService.BASE_URL}/{space_id}/buyers?{params}"
        )

        # Check cache
        cached_data = await CacheRepository.get_cache(db, cache_key=cache_key)
        if cached_data:
            return UriResponse.get_single_data_response("buyers", cached_data)

        # Make request
        response = requests.get(
            f"{XSpacesLookupService.BASE_URL}/{space_id}/buyers",
            headers=headers,
            params=params,
        )
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get(
                    "error", "Failed to get buyers for the Space."
                ),
            )

        result = response.json()
        # Cache the response
        await CacheRepository.set_cache(
            db=db, cache_key=cache_key, data=result, ttl=XSpacesLookupService.CACHE_TTL
        )

        return UriResponse.get_single_data_response("buyers", result)
