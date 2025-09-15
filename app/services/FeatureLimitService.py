from typing import Callable, Dict, Optional
from app.domain.enums.endpoints_enum import EndpointsEnum
from app.repository.InfluencerRepository import InfluencerRepository
from app.repository.TrackerRepository import TrackerRepository
from app.services.uri_microservices.UriTaskManagerService import UriTaskManagerService
from motor.motor_asyncio import AsyncIOMotorDatabase


class FeatureLimitService:
    ACCOUNT_TRACKING_ENDPOINTS = [
        EndpointsEnum.SAVE_LINKEDIN_ACCOUNTS.value,
        EndpointsEnum.SAVE_INSTAGRAM_ACCOUNTS.value,
        EndpointsEnum.SAVE_FACEBOOK_ACCOUNTS.value,
    ]

    @staticmethod
    async def sync_specific_feature_limit_for_user(
        db: AsyncIOMotorDatabase,
        user_id: str,
        endpoint: str,
        social_platform: Optional[str] = None,
    ):
        update_functions: Dict[str, Callable] = {
            "account_tracking": FeatureLimitService._sync_account_tracking_limit,
            EndpointsEnum.KEYWORD_TRACKIING.value: lambda **kwargs: FeatureLimitService._sync_tracker_limit(
                db=kwargs["db"],
                user_id=kwargs["user_id"],
                tracker_type="KEYWORD",
                endpoint_enum=EndpointsEnum.KEYWORD_TRACKIING,
            ),
            EndpointsEnum.HASHTAG_TRACKING.value: lambda **kwargs: FeatureLimitService._sync_tracker_limit(
                db=kwargs["db"],
                user_id=kwargs["user_id"],
                tracker_type="HASHTAG",
                endpoint_enum=EndpointsEnum.HASHTAG_TRACKING,
            ),
        }

        if endpoint in FeatureLimitService.ACCOUNT_TRACKING_ENDPOINTS:
            if not social_platform:
                print("Social platform not specified")
                return None
            return await update_functions.get(
                "account_tracking", FeatureLimitService._sync_account_tracking_limit
            )(
                db=db,
                user_id=user_id,
                social_platform=social_platform,
                endpoint=endpoint,
            )

        update_function = update_functions.get(endpoint)
        if not update_function:
            print("Unsupported endpoint provided")
            return None

        return await update_function(db=db, user_id=user_id)

    async def _sync_account_tracking_limit(db, user_id, social_platform, endpoint):
        user_influencer_count = (
            await InfluencerRepository.get_user_influencer_count_by_filters(
                db, user_id=user_id, platforms=[social_platform]
            )
        )
        updated_feature_limit_response = (
            await UriTaskManagerService.update_user_feature_limit_specific_limit(
                user_id, endpoint, user_influencer_count
            )
        )
        if not updated_feature_limit_response.get("status"):
            print(f"Updating feature limit for user {user_id} failed")

    @staticmethod
    async def _sync_tracker_limit(
        db: AsyncIOMotorDatabase,
        user_id: str,
        tracker_type: str,
        endpoint_enum: EndpointsEnum,
    ):
        tracker_count = await TrackerRepository.get_trackers_count_by_filter(
            db=db, user_id=user_id, tracker_type=tracker_type
        )
        updated_feature_limit_response = (
            await UriTaskManagerService.update_user_feature_limit_specific_limit(
                user_id,
                endpoint_enum.value,
                tracker_count,
            )
        )
        if (
            not updated_feature_limit_response
            or not updated_feature_limit_response.get("status")
        ):
            print(
                f"Updating {tracker_type.lower()} feature limit for user {user_id} failed"
            )
