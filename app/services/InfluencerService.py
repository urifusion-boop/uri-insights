from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.enums.endpoints_enum import EndpointsEnum
from app.domain.schemas import influencer_schema
from app.repository.InfluencerRepository import InfluencerRepository
from app.services.FeatureLimitService import FeatureLimitService


class InfluencerService:
    @staticmethod
    def _get_endpoint_enum_from_platform(platform: str):
        endpoint_enums = {
            "LINKEDIN": EndpointsEnum.SAVE_LINKEDIN_ACCOUNTS.value,
            "FACEBOOK": EndpointsEnum.SAVE_FACEBOOK_ACCOUNTS.value,
            "INSTAGRAM": EndpointsEnum.SAVE_INSTAGRAM_ACCOUNTS.value,
        }
        endpoint = endpoint_enums.get(platform)
        if not endpoint:
            raise ValueError("Unsupported platform: ", platform)
        return endpoint

    @staticmethod
    async def create_influencer(
        db: AsyncIOMotorDatabase,
        influencer: influencer_schema.InfluencerCreate,
    ):
        created_response = await InfluencerRepository.create_influencer(db, influencer)
        if not created_response.get("status"):
            print("Failed to create influencer: ", influencer.dict())

        social_platform = influencer.social_platform

        if social_platform:
            endpoint = InfluencerService._get_endpoint_enum_from_platform(
                social_platform.value
            )

            await FeatureLimitService.sync_specific_feature_limit_for_user(
                db, influencer.user_id, endpoint, social_platform.value
            )
        return created_response

    @staticmethod
    async def delete_influencer(
        db: AsyncIOMotorDatabase,
        influencer_id: str,
    ):
        deleted_response = await InfluencerRepository.delete_influencer(
            db, influencer_id
        )

        if deleted_response.get("status", False):
            user_id = deleted_response.get("responseData", {}).get("user_id", "")
            social_platform = deleted_response.get("responseData", {}).get(
                "social_platform", ""
            )
            endpoint = InfluencerService._get_endpoint_enum_from_platform(
                social_platform
            )

            await FeatureLimitService.sync_specific_feature_limit_for_user(
                db, user_id, endpoint, social_platform
            )
        return deleted_response
