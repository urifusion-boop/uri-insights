from datetime import timedelta
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repository.CacheRepository import CacheRepository
from app.core.helpers.cache_helper import CacheHelper
from app.domain.responses.uri_response import UriResponse
from app.domain.requests.twitter_requests import (
    CurrentUserLookupParams,
    TimelineParams,
    MentionsParams,
)
from app.services.XTimelineService import XTimelineService
from app.services.XUsersLookupService import XUsersLookupService
from app.domain.responses.uri_response import UriResponse
from app.domain.schemas import influencer_schema
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repository.InfluencerRepository import InfluencerRepository
from app.domain.enums.account_enum import AccountTypeEnum


class TwitterService:
    BASE_URL = "https://api.x.com/2/users"
    CACHE_TTL = timedelta(minutes=15)  # Cache for 15 minutes

    @staticmethod
    async def save_twitter_account(
        db: AsyncIOMotorDatabase, user_id: str, access_token: str
    ):
        # Get Twitter user data using the access token
        twitter_user = TwitterService.get_twitter_user(db, access_token)

        if twitter_user:
            # Prepare the influencer data
            influencer_data = influencer_schema.InfluencerCreate(
                user_id=user_id,
                social_name=twitter_user.get("name", ""),
                profile_pic=twitter_user.get("profile_image_url", ""),
                social_user_id=twitter_user.get("id", ""),
                social_username=twitter_user.get("username", ""),
                social_platform="TWITTER",
                account_type=AccountTypeEnum.PERSONAL,
                connected=True,
                token=access_token,
            )

            # Perform a create or update operation
            await InfluencerRepository.create_or_update_influencer(db, influencer_data)

            # Fetch all influencers by user_id
            influencer_list = InfluencerRepository.get_influencers_by_filter(
                db, user_id=user_id
            )

            # Return the influencer accounts as a response
            return UriResponse.get_single_data_response(
                "influencer accounts", influencer_list
            )

        # Return response when Twitter user data is not found
        return UriResponse.get_single_data_response("influencer account", None)

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

        twitter_user = TwitterService.get_twitter_user(db, access_token)
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

    @staticmethod
    def get_twitter_user(db: AsyncIOMotorDatabase, access_token: str):
        discovery_data = XUsersLookupService.get_current_user(
            access_token=access_token, params=CurrentUserLookupParams()
        )

        print("Discovery Data : ", discovery_data)

        if discovery_data.get("status") is not True:
            print("Failed to fetch business discovery data")
            return None  # Return early if discovery fails

        twitter_user = discovery_data.get("responseData", {}).get("data", {})
        return twitter_user

    @staticmethod
    def get_user_tweets(
        db: AsyncIOMotorDatabase, user_id: str, access_token: str, next: Optional[str]
    ):
        params = TimelineParams()
        if next:
            params.pagination_token = next
        tweet_data = XTimelineService.get_user_tweets(
            db=db,
            user_id=user_id,
            access_token=access_token,
            params=params,
        )
        return tweet_data

    @staticmethod
    def get_user_mentions(
        db: AsyncIOMotorDatabase, user_id: str, access_token: str, next: Optional[str]
    ):
        params = TimelineParams()
        if next:
            params.pagination_token = next
        tweet_data = XTimelineService.get_user_mentions(
            db=db,
            user_id=user_id,
            access_token=access_token,
            params=params,
        )
        return tweet_data

    @staticmethod
    def get_reverse_chronological_timeline(
        db: AsyncIOMotorDatabase,
        social_user_id: str,
        access_token: str,
        start_time: Optional[str],
        end_time: Optional[str],
        next: Optional[str],
        exclude: Optional[str],
    ):
        params = TimelineParams()
        if start_time:
            params.start_time = start_time
        if end_time:
            params.start_time = end_time
        if end_time:
            params.pagination_token = next
        if end_time:
            params.exclude = exclude

        timeline_data = XTimelineService.get_reverse_chronological_timeline(
            db=db,
            user_id=social_user_id,
            access_token=access_token,
            params=params,
        )
        return timeline_data
