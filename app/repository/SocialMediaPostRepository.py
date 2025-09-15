from typing import Dict, List, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime, date, time
from app.domain.schemas.socialmediapost_schema import (
    SocialMediaPost,
    SocialMediaPostCreate,
    SocialMediaPostUpdate,
)
from app.domain.responses.uri_response import UriResponse


class SocialMediaPostRepository:
    @staticmethod
    async def create_post(
        db: AsyncIOMotorDatabase, post: SocialMediaPostCreate
    ) -> Dict[str, Any]:
        post_data = post.dict()
        post_data["post_id"] = str(ObjectId())
        post_data["created_date"] = datetime.now().isoformat()
        post_data["last_updated"] = datetime.now().isoformat()

        if "start_date" in post_data and isinstance(post_data["start_date"], date):
            post_data["start_date"] = post_data["start_date"].isoformat()
        if "start_time" in post_data and isinstance(post_data["start_time"], time):
            post_data["start_time"] = post_data["start_time"].isoformat()

        await db["social_media_posts"].insert_one(post_data)

        return UriResponse.create_response(
            "social_media_post", SocialMediaPost(**post_data).dict()
        )

    @staticmethod
    async def update_post(
        db: AsyncIOMotorDatabase, model: SocialMediaPostUpdate
    ) -> Dict[str, Any]:
        updates_data = model.dict(exclude_unset=True)
        updates_data["last_updated"] = datetime.now().isoformat()

        if "start_date" in updates_data and isinstance(
            updates_data["start_date"], date
        ):
            updates_data["start_date"] = updates_data["start_date"].isoformat()
        if "start_time" in updates_data and isinstance(
            updates_data["start_time"], time
        ):
            updates_data["start_time"] = updates_data["start_time"].isoformat()

        result = await db["social_media_posts"].update_one(
            {"post_id": model.post_id}, {"$set": updates_data}
        )

        if result.matched_count == 0:
            return UriResponse.get_single_data_response("social_media_post", None)

        updated_post = await db["social_media_posts"].find_one(
            {"post_id": model.post_id}
        )
        return UriResponse.update_response(
            "social_media_post", SocialMediaPost(**updated_post).dict()
        )

    @staticmethod
    async def get_post_by_id(db: AsyncIOMotorDatabase, post_id: str) -> Dict[str, Any]:
        post = await db["social_media_posts"].find_one({"post_id": post_id})
        return UriResponse.get_single_data_response(
            "social_media_post", SocialMediaPost(**post).dict() if post else None
        )

    @staticmethod
    async def get_posts_by_filters(
        db: AsyncIOMotorDatabase,
        user_id: str,
        platform: Optional[str] = None,
        status: Optional[str] = None,
        post_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 10,
    ) -> Dict[str, Any]:
        query: Dict[str, Any] = {"user_id": user_id}

        if platform is not None:
            query["platform"] = platform
        if status is not None:
            query["status"] = status
        if post_type is not None:
            query["post_type"] = post_type

        total_posts = await db["social_media_posts"].count_documents(query)
        cursor = (
            db["social_media_posts"]
            .find(query)
            .sort("created_date", -1)
            .skip(skip)
            .limit(limit)
        )
        posts = await cursor.to_list(length=limit)

        posts_list = [SocialMediaPost(**post).dict() for post in posts]
        return UriResponse.get_paged_data_response(
            "social_media_post", posts_list, total_posts, skip + 1, limit
        )

    @staticmethod
    async def delete_post(db: AsyncIOMotorDatabase, post_id: str) -> Dict[str, Any]:
        result = await db["social_media_posts"].delete_one({"post_id": post_id})

        if result.deleted_count == 0:
            return UriResponse.delete_response(
                "social_media_post", False, "Post not found."
            )

        return UriResponse.delete_response("social_media_post", True)

    @staticmethod
    async def multiple_create_posts(
        db: AsyncIOMotorDatabase, posts: List[SocialMediaPostCreate]
    ) -> Dict[str, Any]:
        post_data_list = []

        for post in posts:
            post_data = post.dict()
            post_data["post_id"] = str(ObjectId())
            post_data["created_date"] = datetime.now().isoformat()
            post_data["last_updated"] = datetime.now().isoformat()

            if "start_date" in post_data and isinstance(post_data["start_date"], date):
                post_data["start_date"] = post_data["start_date"].isoformat()
            if "start_time" in post_data and isinstance(post_data["start_time"], time):
                post_data["start_time"] = post_data["start_time"].isoformat()
            if "end_date" in post_data and isinstance(post_data["end_date"], date):
                post_data["end_date"] = post_data["end_date"].isoformat()
            if "end_time" in post_data and isinstance(post_data["end_time"], time):
                post_data["end_time"] = post_data["end_time"].isoformat()

            post_data_list.append(post_data)

        await db["social_media_posts"].insert_many(post_data_list)

        created_posts = [SocialMediaPost(**post).dict() for post in post_data_list]
        return UriResponse.create_multiple_response("social_media_post", created_posts)

    @staticmethod
    async def update_post_status(
        db: AsyncIOMotorDatabase, post_id: str, status: str
    ) -> Dict[str, Any]:
        result = await db["social_media_posts"].update_one(
            {"post_id": post_id},
            {"$set": {"status": status, "last_updated": datetime.now().isoformat()}},
        )

        if result.matched_count == 0:
            return UriResponse.get_single_data_response(
                "social_media_post", None, "Post not found."
            )

        updated_post = await db["social_media_posts"].find_one({"post_id": post_id})
        return UriResponse.update_response(
            "social_media_post", SocialMediaPost(**updated_post).dict()
        )

    @staticmethod
    async def search_posts(
        db: AsyncIOMotorDatabase, query: str, skip: int = 0, limit: int = 10
    ):
        search_query = {
            "$or": [
                {"content": {"$regex": query, "$options": "i"}},
                {"hashtags": {"$regex": query, "$options": "i"}},
                {"mentions": {"$regex": query, "$options": "i"}},
            ]
        }

        total = await db["social_media_posts"].count_documents(search_query)
        cursor = (
            db["social_media_posts"]
            .find(search_query)
            .sort("created_date", -1)
            .skip(skip)
            .limit(limit)
        )
        posts = await cursor.to_list(length=limit)

        posts_list = [SocialMediaPost(**post) for post in posts]
        return UriResponse.get_paged_data_response(
            "social_media_posts", posts_list, total, skip + 1, limit
        )
