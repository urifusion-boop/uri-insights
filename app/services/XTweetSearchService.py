from datetime import timedelta
import requests
from http import HTTPStatus
from typing import Optional, Dict, Any
from fastapi import HTTPException
from app.core.helpers.twitter_helper import TwitterHelper
from app.domain.responses.uri_response import UriResponse
from app.repository.CacheRepository import CacheRepository
from app.core.helpers.cache_helper import CacheHelper
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.requests.twitter_requests import TweetSearchParams
from app.core.config import settings
from app.core.helpers.text_helper import TextHelper


class XTweetSearchService:
    BASE_URL = "https://api.x.com/2/tweets/search/"
    CACHE_TTL = timedelta(hours=24)  # Cache for 15 minutes

    @staticmethod
    async def search_all_tweets(
        db: AsyncIOMotorDatabase, params: TweetSearchParams, access_token: Optional[str]
    ) -> Dict[str, Any]:
        """
        Perform a full-archive search for tweets using the X API.
        :param params: Pydantic model containing query parameters.
        :param access_token: Bearer token for authentication.
        :return: JSON response from the API.
        """
        access_token = access_token or settings.X_APP_BEARER_TOKEN

        print("Access token : ", f"{access_token}")

        query_string = TextHelper.construct_query_url(
            params
        )  # Encode parameters into a query string

        full_url = f"{XTweetSearchService.BASE_URL}all?{query_string}"
        headers = {"Authorization": f"Bearer {access_token}"}

        # Generate cache key
        cache_key = CacheHelper.generate_cache_key(f"{full_url}")

        print("FULL SEARCH ALL TWEET URL : ", f"{full_url}")

        # Check cache
        cached_data = await CacheRepository.get_cache(
            db, cache_key=cache_key
        )  # Replace `None` with a valid `db` if required
        if cached_data:
            return UriResponse.get_single_data_response("tweets", cached_data)

        # Make request
        response = requests.get(full_url, headers=headers)

        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("error", "Failed to fetch tweets."),
            )

        result = response.json()

        # Cache the response
        await CacheRepository.set_cache(
            db=None, cache_key=cache_key, data=result, ttl=XTweetSearchService.CACHE_TTL
        )

        return UriResponse.get_single_data_response("tweets", result)

    @staticmethod
    async def search_recent_tweets_v1(
        db: AsyncIOMotorDatabase, params: TweetSearchParams
    ) -> Dict[str, Any]:
        """
        Perform a recent search for tweets using the X API.
        :param params: Pydantic model containing query parameters.
        :return: JSON response from the API.
        """
        # Ensure access_token is provided and sanitized
        access_token = settings.X_APP_BEARER_TOKEN.strip()

        print("Access token : ", f"{access_token}")

        query_parts = [params.query]

        # Add included keywords
        if params.includes:
            query_parts.extend(params.includes)

        # Add excluded keywords
        if params.excludes:
            query_parts.extend(f"-{word}" for word in params.excludes)

        # Add additional filters dynamically
        if params.hashtags:
            query_parts.extend(f"#{tag}" for tag in params.hashtags)

        if params.min_retweets:
            query_parts.append(f"min_retweets:{params.min_retweets}")

        if params.min_likes:
            query_parts.append(f"min_faves:{params.min_likes}")

        if params.min_replies:
            query_parts.append(f"min_replies:{params.min_replies}")

        if params.languages:
            language_filters = [f"lang:{lang}" for lang in params.languages]
            query_parts.extend(language_filters)

        if params.from_user:
            query_parts.append(f"from:{params.from_user}")

        if params.to_user:
            query_parts.append(f"to:{params.to_user}")

        if params.is_reply:
            query_parts.append("is:reply")

        if params.is_retweet:
            query_parts.append("is:retweet")

        # Combine the query parts
        full_query = " ".join(query_parts)

        query_params = {
            "query": full_query,
            "since_id": params.since_id,
            "until_id": params.until_id,
            "sort_order": params.sort,
            "expansions": params.expansions,
            "tweet.fields": params.tweet_fields,
            "user.fields": params.user_fields,
            "media.fields": params.media_fields,
            "place.fields": params.place_fields,
            "poll.fields": params.poll_fields,
            "max_results": params.max_results,
            "pagination_token": params.pagination_token,
            "start_time": params.start_time,
            "end_time": params.end_time,
        }

        # Construct the query string
        query_string = TextHelper.construct_query_url(query_params)
        full_url = f"{XTweetSearchService.BASE_URL}recent?{query_string}"

        headers = {"Authorization": f"Bearer {access_token}"}

        # Generate cache key
        cache_key = CacheHelper.generate_cache_key(full_url)

        print("FULL SEARCH RECENT TWEET URL : ", full_url)

        # Check cache
        cached_data = await CacheRepository.get_cache(db, cache_key)
        if cached_data:
            return UriResponse.get_single_data_response(
                "tweets", {**cached_data, "cache_key": cache_key}
            )

        # Make request
        response = requests.get(full_url, headers=headers)
        print("FULL SEARCH RECENT TWEET RESPONSE : ", response.json())

        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("error", "Failed to fetch recent tweets."),
            )

        result = response.json()
        print("FULL SEARCH RECENT TWEET RESULT : ", result)

        # Cache the response
        await CacheRepository.set_cache(
            db=db, cache_key=cache_key, data=result, ttl=XTweetSearchService.CACHE_TTL
        )

        # Filter locations if requested
        if params.locations:
            result["data"] = [
                tweet
                for tweet in result.get("data", [])
                if tweet.get("geo", {}).get("place_id") in params.locations
            ]

        return UriResponse.get_single_data_response(
            "tweets", {**result, "twitter_cache_key": cache_key}
        )

    @staticmethod
    async def search_recent_tweets(
        db: AsyncIOMotorDatabase, params: TweetSearchParams
    ) -> Dict[str, Any]:
        """
        Perform a recent search for tweets using the Twitter API.
        :param params: Pydantic model containing query parameters.
        :return: JSON response from the API with enriched user data.
        """
        # Ensure access_token is provided and sanitized
        access_token = settings.X_APP_BEARER_TOKEN.strip()
        print("Access token : ", f"{access_token}")

        query_parts_one = [params.query]
        query_parts_two = []

        # Add included keywords
        if params.includes:
            query_parts_two.extend(params.includes)

        # Add excluded keywords
        if params.excludes:
            query_parts_two.extend(f"-{word}" for word in params.excludes)

        # Add additional filters dynamically
        if params.hashtags:
            query_parts_two.extend(f"#{tag}" for tag in params.hashtags)

        if params.min_retweets:
            query_parts_two.append(f"min_retweets:{params.min_retweets}")

        if params.min_likes:
            query_parts_two.append(f"min_faves:{params.min_likes}")

        if params.min_replies:
            query_parts_two.append(f"min_replies:{params.min_replies}")

        if params.languages:
            language_filters = [f"lang:{lang}" for lang in params.languages]
            query_parts_two.extend(language_filters)

        if params.from_user:
            query_parts_two.append(f"from:{params.from_user}")

        if params.to_user:
            query_parts_two.append(f"to:{params.to_user}")

        if params.is_reply:
            query_parts_two.append("is:reply")

        if params.is_retweet:
            query_parts_two.append("is:retweet")

        # Combine the query parts
        full_query = TwitterHelper.trunc_twitter_query(
            query_parts_one=query_parts_one, query_parts_two=query_parts_two
        )

        query_params = {
            "query": full_query,
            "since_id": params.since_id,
            "until_id": params.until_id,
            "sort_order": params.sort,
            "expansions": params.expansions,
            "tweet.fields": params.tweet_fields,
            "user.fields": params.user_fields,
            "media.fields": params.media_fields,
            "place.fields": params.place_fields,
            "poll.fields": params.poll_fields,
            "max_results": params.max_results,
            "pagination_token": params.pagination_token,
            "start_time": params.start_time,
            "end_time": params.end_time,
        }

        # Construct the query string
        query_string = TextHelper.construct_query_url(query_params)
        full_url = f"{XTweetSearchService.BASE_URL}recent?{query_string}"

        headers = {"Authorization": f"Bearer {access_token}"}

        # Generate cache key
        cache_key = CacheHelper.generate_cache_key(full_url)

        print("FULL SEARCH RECENT TWEET URL : ", full_url)

        # Check cache
        cached_data = await CacheRepository.get_cache(db, cache_key)
        if cached_data:
            return UriResponse.get_single_data_response(
                "tweets", {**cached_data, "cache_key": cache_key}
            )

        # Make request
        response = requests.get(full_url, headers=headers)
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("error", "Failed to fetch recent tweets."),
            )

        result = response.json()

        # Cache the response
        await CacheRepository.set_cache(
            db=db, cache_key=cache_key, data=result, ttl=XTweetSearchService.CACHE_TTL
        )

        # Map `author_id` to corresponding user details
        # includes_users = result.get("includes", {}).get("users", [])
        # user_mapping = {user["id"]: user for user in includes_users}

        # # Enrich tweet data with user details
        # for tweet in result.get("data", []):
        #     author_id = tweet.get("author_id")
        #     if author_id in user_mapping:
        #         tweet["author"] = {
        #             "id": author_id,
        #             "username": user_mapping[author_id].get("username"),
        #             "profile_image_url": user_mapping[author_id].get(
        #                 "profile_image_url"
        #             ),
        #             "verified": user_mapping[author_id].get("verified"),
        #             "followers_count": user_mapping[author_id]
        #             .get("public_metrics", {})
        #             .get("followers_count"),
        #         }

        return UriResponse.get_single_data_response(
            "tweets", {**result, "twitter_cache_key": cache_key}
        )
