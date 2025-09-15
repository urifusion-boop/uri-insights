from typing import Any, Dict, List
from app.domain.enums.reportgeneration_enum import ReportGenerationTypeEnum as FeatName
from app.domain.enums.socialmediapost_enum import PostPlatformEnum
from app.services.EmbeddingService import EmbeddingService
from motor.motor_asyncio import AsyncIOMotorDatabase


class AccountTrackingHelper:
    @staticmethod
    async def trigger_account_tracking_post_embedding_process(
        db: AsyncIOMotorDatabase,
        influencer_data: Dict[str, Any],
        posts: List[Dict[str, Any]],
        platform: PostPlatformEnum,
    ):
        social_user_id = influencer_data.get("social_user_id")

        account_tracking_embedded_items = await EmbeddingService.bulk_process_items(
            db=db,
            feature_name=FeatName.ACCOUNT_TRACKING,
            items=posts,
            social_user_id=social_user_id,
            platform=platform,
        )
        print("Account Tracking Embedded Items: ", account_tracking_embedded_items)
