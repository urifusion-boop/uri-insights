from datetime import timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase

from fastapi import HTTPException
from http import HTTPStatus
from app.repository.CacheRepository import CacheRepository
from app.core.helpers.cache_helper import CacheHelper
from app.domain.responses.uri_response import UriResponse
import requests
from typing import Dict, Any, Optional
from app.domain.requests.twitter_requests import TweetLookupParams, SingleTweetParams


class TweetLookupService:
    BASE_URL_TWEETS_LOOKUP = "https://api.x.com/2/tweets"
    CACHE_TTL = timedelta(minutes=15)  # Cache for 15 minutes

    @staticmethod
    async def get_tweets(
        db: AsyncIOMotorDatabase, params: TweetLookupParams, access_token: str
    ) -> Dict[str, Any]:
        """
        Fetch details for one or more Tweets by their IDs.
        :param db: AsyncIOMotorDatabase instance for caching.
        :param params: Pydantic model containing query parameters.
        :param access_token: Bearer token for authentication.
        :return: JSON response from the API.
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        params_dict = params.dict(exclude_none=True)  # Convert Pydantic model to a dict

        # Generate cache key
        cache_key = CacheHelper.generate_cache_key(
            f"{TweetLookupService.BASE_URL_TWEETS_LOOKUP}{params_dict}"
        )

        # Check cache
        cached_data = await CacheRepository.get_cache(db, cache_key=cache_key)
        if cached_data:
            return UriResponse.get_single_data_response("tweets", cached_data)

        # Make request
        response = requests.get(
            TweetLookupService.BASE_URL_TWEETS_LOOKUP,
            headers=headers,
            params=params_dict,
        )

        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("error", "Failed to fetch tweets."),
            )

        result = response.json()

        # Cache the response
        await CacheRepository.set_cache(
            db=db, cache_key=cache_key, data=result, ttl=TweetLookupService.CACHE_TTL
        )

        return UriResponse.get_single_data_response("tweets", result)

    @staticmethod
    async def get_tweet_by_id(
        db: AsyncIOMotorDatabase,
        tweet_id: str,
        params: Optional[SingleTweetParams],
        access_token: str,
    ) -> Dict[str, Any]:
        """
        Fetch details for a single Tweet by its ID.
        :param db: AsyncIOMotorDatabase instance for caching.
        :param tweet_id: ID of the Tweet to retrieve.
        :param params: Pydantic model containing optional query parameters.
        :param access_token: Bearer token for authentication.
        :return: JSON response from the API.
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        params_dict = params.dict(exclude_none=True) if params else {}

        # Generate cache key
        cache_key = CacheHelper.generate_cache_key(
            f"{TweetLookupService.BASE_URL_TWEETS_LOOKUP}/{tweet_id}{params_dict}"
        )

        # Check cache
        cached_data = await CacheRepository.get_cache(db, cache_key=cache_key)
        if cached_data:
            return UriResponse.get_single_data_response("tweet", cached_data)

        # Construct the URL
        url = f"{TweetLookupService.BASE_URL_TWEETS_LOOKUP}/{tweet_id}"

        # Make request
        response = requests.get(url, headers=headers, params=params_dict)

        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("error", "Failed to fetch tweet."),
            )

        result = response.json()

        # Cache the response
        await CacheRepository.set_cache(
            db=db, cache_key=cache_key, data=result, ttl=TweetLookupService.CACHE_TTL
        )

        return UriResponse.get_single_data_response("tweet", result)

    BASE_URL_TWEETS_LOOKUP = "https://api.x.com/2/tweets"
    CACHE_TTL = timedelta(minutes=15)  # Cache for 15 minutes
