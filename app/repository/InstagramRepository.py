from typing import Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorDatabase
from app import schemas


class InstagramRepository:
    @staticmethod
    async def create_instagram_insights(
        db: AsyncIOMotorDatabase, insights: schemas.InstagramInsightsCreate
    ) -> Dict[str, Any]:
        db_insights = {
            "user_id": insights.user_id,
            "ig_user_id": insights.ig_user_id,
            "data": insights.data,
        }
        result = await db["instagram_insights"].insert_one(db_insights)
        db_insights["_id"] = result.inserted_id
        return db_insights

    @staticmethod
    async def get_instagram_insights(
        db: AsyncIOMotorDatabase, user_id: str, ig_user_id: str
    ) -> Any:
        return await db["instagram_insights"].find_one(
            {"user_id": user_id, "ig_user_id": ig_user_id}
        )

    @staticmethod
    async def update_instagram_insights(
        db: AsyncIOMotorDatabase, user_id: str, ig_user_id: str, data: dict
    ) -> Any:
        result = await db["instagram_insights"].update_one(
            {"user_id": user_id, "ig_user_id": ig_user_id},
            {"$set": {"data": data}},
            upsert=True,
        )
        if result.matched_count == 0:
            return None
        return await db["instagram_insights"].find_one(
            {"user_id": user_id, "ig_user_id": ig_user_id}
        )

    @staticmethod
    async def delete_instagram_insights(
        db: AsyncIOMotorDatabase, user_id: str, ig_user_id: str
    ) -> Any:
        result = await db["instagram_insights"].delete_one(
            {"user_id": user_id, "ig_user_id": ig_user_id}
        )
        return result.deleted_count > 0

    @staticmethod
    async def create_facebook_user_pages(
        db: AsyncIOMotorDatabase, pages: schemas.FacebookUserPagesCreate
    ) -> Dict[str, Any]:
        db_user_facebook_pages = {
            "user_id": pages.user_id,
            "data": pages.data,
        }
        result = await db["facebook_user_pages"].insert_one(db_user_facebook_pages)
        db_user_facebook_pages["_id"] = result.inserted_id
        return db_user_facebook_pages

    @staticmethod
    async def update_facebook_user_pages(
        db: AsyncIOMotorDatabase, user_id: str, data: dict
    ) -> Any:
        result = await db["facebook_user_pages"].update_one(
            {"user_id": user_id},
            {"$set": {"data": data}},
            upsert=True,
        )
        if result.matched_count == 0:
            return None
        return await db["facebook_user_pages"].find_one({"user_id": user_id})
