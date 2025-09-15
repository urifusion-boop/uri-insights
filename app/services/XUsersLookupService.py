from datetime import timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase

from fastapi import HTTPException
from http import HTTPStatus
from app.repository.CacheRepository import CacheRepository
from app.core.helpers.cache_helper import CacheHelper
from app.domain.responses.uri_response import UriResponse
import requests
from typing import Dict, Any, Optional
from app.domain.requests.twitter_requests import (
    UsersLookupParams,
    CurrentUserLookupParams,
    TimelineParams,
)
from app.core.helpers.text_helper import TextHelper
from app.services.XTimelineService import XTimelineService


class XUsersLookupService:
    BASE_URL = "https://api.x.com/2/users"
    CACHE_TTL = timedelta(minutes=15)  # Cache for 15 minutes

    @staticmethod
    async def get_users_by_ids(
        db: AsyncIOMotorDatabase, ids: str, params: UsersLookupParams, access_token: str
    ) -> Dict[str, Any]:
        """
        Fetch details of users specified by IDs.
        :param db: AsyncIOMotorDatabase instance for caching.
        :param ids: Comma-separated string of user IDs (max 100).
        :param params: Query parameters for the request.
        :param access_token: Bearer token for authentication.
        :return: JSON response from the API.
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        params_dict = {"ids": ids, **params.dict(exclude_none=True)}

        # Generate cache key
        cache_key = CacheHelper.generate_cache_key(
            f"{XUsersLookupService.BASE_URL}?{params_dict}"
        )

        # Check cache
        cached_data = await CacheRepository.get_cache(db, cache_key=cache_key)
        if cached_data:
            return UriResponse.get_single_data_response("users", cached_data)

        # Make request
        url = f"{XUsersLookupService.BASE_URL}"
        response = requests.get(url, headers=headers, params=params_dict)

        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("error", "Failed to fetch user details."),
            )

        result = response.json()

        # Cache the response
        await CacheRepository.set_cache(
            db=db, cache_key=cache_key, data=result, ttl=XUsersLookupService.CACHE_TTL
        )

        return UriResponse.get_single_data_response("users", result)

    @staticmethod
    async def get_user_by_id(
        db: AsyncIOMotorDatabase,
        user_id: str,
        params: UsersLookupParams,
        access_token: str,
    ) -> Dict[str, Any]:
        """
        Fetch details of a single user by their ID.
        :param db: AsyncIOMotorDatabase instance for caching.
        :param user_id: Twitter user ID to fetch details for.
        :param params: Query parameters for the request.
        :param access_token: Bearer token for authentication.
        :return: JSON response from the API.
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        params_dict = params.dict(exclude_none=True)

        # Generate cache key
        cache_key = CacheHelper.generate_cache_key(
            f"{XUsersLookupService.BASE_URL}/{user_id}?{params_dict}"
        )

        # Check cache
        cached_data = await CacheRepository.get_cache(db, cache_key=cache_key)
        if cached_data:
            return UriResponse.get_single_data_response("user", cached_data)

        # Make request
        url = f"{XUsersLookupService.BASE_URL}/{user_id}"
        response = requests.get(url, headers=headers, params=params_dict)

        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("error", "Failed to fetch user details."),
            )

        result = response.json()

        # Cache the response
        await CacheRepository.set_cache(
            db=db, cache_key=cache_key, data=result, ttl=XUsersLookupService.CACHE_TTL
        )

        return UriResponse.get_single_data_response("user", result)

    @staticmethod
    async def get_user_by_username(
        db: AsyncIOMotorDatabase,
        username: str,
        params: UsersLookupParams,
        access_token: str,
    ) -> Dict[str, Any]:
        """
        Fetch details of a single user by their username.
        :param db: AsyncIOMotorDatabase instance for caching.
        :param username: Twitter username to fetch details for.
        :param params: Query parameters for the request.
        :param access_token: Bearer token for authentication.
        :return: JSON response from the API.
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        params_dict = params.dict(exclude_none=True)

        # Generate cache key
        cache_key = CacheHelper.generate_cache_key(
            f"{XUsersLookupService.BASE_URL}/by/username/{username}?{params_dict}"
        )

        # Check cache
        cached_data = await CacheRepository.get_cache(db, cache_key=cache_key)
        if cached_data:
            return UriResponse.get_single_data_response("user", cached_data)

        # Make request
        url = f"{XUsersLookupService.BASE_URL}/by/username/{username}"
        response = requests.get(url, headers=headers, params=params_dict)

        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("error", "Failed to fetch user details."),
            )

        result = response.json()

        # Cache the response
        await CacheRepository.set_cache(
            db=db, cache_key=cache_key, data=result, ttl=XUsersLookupService.CACHE_TTL
        )

        return UriResponse.get_single_data_response("user", result)

    @staticmethod
    def get_current_user(
        access_token: str,
        params: Optional[CurrentUserLookupParams],
    ) -> Dict[str, Any]:
        """
        Fetch details of the currently authenticated user.
        :param db: AsyncIOMotorDatabase instance for caching.
        :param params: Query parameters for the request.
        :param access_token: Bearer token for authentication.
        :return: JSON response from the API.
        """

        if params is None:
            params = CurrentUserLookupParams()

        print("Params : ", params)
        headers = {"Authorization": f"Bearer {access_token}"}

        # # Generate cache key
        # cache_key = CacheHelper.generate_cache_key(
        #     f"{XUsersLookupService.BASE_URL}/me?{params_dict}"
        # )

        # # Check cache
        # cached_data = await CacheRepository.get_cache(db, cache_key=cache_key)
        # if cached_data:
        #     return UriResponse.get_single_data_response("user", cached_data)

        # Make request
        query_params = {
            "expansions": params.expansions,
            "tweet.fields": params.tweet_fields,
            "user.fields": params.user_fields,
        }

        # Construct the query string
        query_string = TextHelper.construct_query_url(query_params)
        url = f"{XUsersLookupService.BASE_URL}/me?{query_string}"
        response = requests.get(url, headers=headers)

        print("X Cirrent User Url : ", url)
        print("X Users Response : ", response.json())

        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get(
                    "error", "Failed to fetch current user details."
                ),
            )

        result = response.json()

        print("X Users Result : ", result)
        # Cache the response
        # CacheRepository.set_cache(
        #     db=db, cache_key=cache_key, data=result, ttl=XUsersLookupService.CACHE_TTL
        # )

        return UriResponse.get_single_data_response("user", result)

    @staticmethod
    async def get_users_by_usernames(
        db: AsyncIOMotorDatabase,
        usernames: str,
        params: UsersLookupParams,
        access_token: str,
    ) -> Dict[str, Any]:
        """
        Fetch details of users specified by their usernames.
        :param db: AsyncIOMotorDatabase instance for caching.
        :param usernames: Comma-separated string of usernames (max 100).
        :param params: Query parameters for the request.
        :param access_token: Bearer token for authentication.
        :return: JSON response from the API.
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        params_dict = {"usernames": usernames, **params.dict(exclude_none=True)}

        # Generate cache key
        cache_key = CacheHelper.generate_cache_key(
            f"{XUsersLookupService.BASE_URL}/by?{params_dict}"
        )

        # Check cache
        cached_data = await CacheRepository.get_cache(db, cache_key=cache_key)
        if cached_data:
            return UriResponse.get_single_data_response("users", cached_data)

        # Make request
        url = f"{XUsersLookupService.BASE_URL}/by"
        response = requests.get(url, headers=headers, params=params_dict)

        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get(
                    "error", "Failed to fetch users by usernames."
                ),
            )

        result = response.json()

        # Cache the response
        await CacheRepository.set_cache(
            db=db, cache_key=cache_key, data=result, ttl=XUsersLookupService.CACHE_TTL
        )

        return UriResponse.get_single_data_response("users", result)

    @staticmethod
    async def fetch_business_discovery(db: AsyncIOMotorDatabase, access_token: str):

        twitter_user_cache_key = (
            "twitter_user_cache_key_" + CacheHelper.generate_cache_key(access_token)
        )

        # Check if cached data exists and is valid
        cached_data = await CacheRepository.get_cache(db, twitter_user_cache_key)
        if cached_data:
            print("Returning cached data")
            return UriResponse.get_single_data_response("account", cached_data)
        # Fetch business discovery data
        discovery_data = XUsersLookupService.get_current_user(
            access_token=access_token, params=CurrentUserLookupParams()
        )

        print("Discovery Data : ", discovery_data)

        if discovery_data.get("status") is not True:
            print("Failed to fetch business discovery data")
            return discovery_data  # Return early if discovery fails

        twitter_user = discovery_data.get("responseData", {}).get("data", {})
        user_id = twitter_user.get("id", None)

        if user_id:
            # Fetch media data
            tweet_data = XTimelineService.get_user_tweets(
                db=db,
                user_id=user_id,
                access_token=access_token,
                params=TimelineParams(),
            )

            print("Tweet Data : ", tweet_data)
            # Combine both discovery and media data
            combined_data = {
                **twitter_user,
                "tweets": tweet_data.get("responseData"),
                "twitter_user_cache_key": twitter_user_cache_key,
            }

        # Cache the fresh response with the provided TTL
        if twitter_user:
            await CacheRepository.set_cache(
                db, twitter_user_cache_key, combined_data, ttl=timedelta(hours=9)
            )

        return UriResponse.get_single_data_response("account", combined_data)
