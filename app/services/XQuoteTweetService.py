from datetime import timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase

from fastapi import HTTPException
from http import HTTPStatus
from app.repository.CacheRepository import CacheRepository
from app.core.helpers.cache_helper import CacheHelper
from app.domain.responses.uri_response import UriResponse
import requests
from typing import Dict, Any
from app.domain.requests.twitter_requests import QuoteTweetsParams


class XQuoteTweetService:
    """
    Service for managing Quote Tweets via the X API.
    Provides methods to:
    - Fetch Quote Tweets for a specific Tweet
    """

    BASE_URL = "https://api.x.com/2/tweets"
    CACHE_TTL = timedelta(minutes=15)  # Cache for 15 minutes

    @staticmethod
    async def get_quote_tweets(
        db: AsyncIOMotorDatabase,
        tweet_id: str,
        params: QuoteTweetsParams,
        access_token: str,
    ) -> Dict[str, Any]:
        """
        Fetches Quote Tweets for a specific Tweet ID.

        :param db: AsyncIOMotorDatabase instance for caching.
        :param tweet_id: Unique identifier of the Tweet.
        :param params: Query parameters for filtering results.
        :param access_token: Bearer token for authentication.
        :return: JSON response containing Quote Tweets.
        """
        headers = {"Authorization": f"Bearer {access_token}"}

        # Generate cache key
        cache_key = CacheHelper.generate_cache_key(
            f"{XQuoteTweetService.BASE_URL}/{tweet_id}/quote_tweets?{params}"
        )

        # Check cache
        cached_data = await CacheRepository.get_cache(db, cache_key=cache_key)
        if cached_data:
            return UriResponse.get_single_data_response("quote_tweets", cached_data)

        # Make API request
        response = requests.get(
            f"{XQuoteTweetService.BASE_URL}/{tweet_id}/quote_tweets",
            headers=headers,
            params=params.dict(exclude_none=True),
        )
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("error", "Failed to retrieve Quote Tweets."),
            )

        result = response.json()
        # Cache response
        await CacheRepository.set_cache(
            db=db, cache_key=cache_key, data=result, ttl=XQuoteTweetService.CACHE_TTL
        )

        return UriResponse.get_single_data_response("quote_tweets", result)
