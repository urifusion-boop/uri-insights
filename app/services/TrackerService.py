from motor.motor_asyncio import AsyncIOMotorDatabase
from app import schemas
from app.domain.enums.endpoints_enum import EndpointsEnum
from app.domain.enums.tracker_enum import TrackerTypeEnum
from app.repository.TrackerRepository import TrackerRepository
from app.services.FeatureLimitService import FeatureLimitService


class TrackerService:
    @staticmethod
    async def create_tracker(
        db: AsyncIOMotorDatabase,
        tracker: schemas.TrackerCreate,
    ):
        tracker_type = tracker.tracker_type
        response_data = await TrackerRepository.create_tracker(db=db, tracker=tracker)

        if tracker_type == TrackerTypeEnum.KEYWORD.value:
            await FeatureLimitService.sync_specific_feature_limit_for_user(
                db, tracker.user_id, EndpointsEnum.KEYWORD_TRACKIING.value
            )
        elif tracker_type == TrackerTypeEnum.HASHTAG.value:
            await FeatureLimitService.sync_specific_feature_limit_for_user(
                db, tracker.user_id, EndpointsEnum.HASHTAG_TRACKING.value
            )

        return response_data

    @staticmethod
    async def delete_tracker(
        tracker_id: str,
        db: AsyncIOMotorDatabase,
    ):
        deleted_response = await TrackerRepository.delete_tracker(db, tracker_id)
        if deleted_response.get("status"):
            deleted_tracker = deleted_response.get("responseData", {})
            tracker_type = deleted_tracker.get("tracker_type")
            user_id = deleted_tracker.get("user_id", "")
            if tracker_type == TrackerTypeEnum.KEYWORD.value:
                await FeatureLimitService.sync_specific_feature_limit_for_user(
                    db, user_id, EndpointsEnum.KEYWORD_TRACKIING.value
                )
            elif tracker_type == TrackerTypeEnum.HASHTAG.value:
                await FeatureLimitService.sync_specific_feature_limit_for_user(
                    db, user_id, EndpointsEnum.HASHTAG_TRACKING.value
                )
        return deleted_response
